function [varargout] = importScan(filenameIn)
%Import a ".scan" file created by the CNDE scanner program.
% This function imports and parses a ".scan" file. This is a custom file
% format that is used by the CNDE scan-controller program.
%
% Example Usage:
%   [x, y, f, Data, Header] = importScan(filename);     % 2D scan file.
%   [x, y, z, f, Data, Header] = importScan(filename);  % 3D scan file.
%
%
% Inputs:
%   filenameIn - Path to the file. If the file has no extension, ".scan"
%       will be automatically appended.
%
% Outputs:
%   x, y, z, ... - Vectors containing the coordinates of each scan point.
%       If the scan is uniform, each vector will contain a unique, sorted,
%       and uniformly increasing list of coordinates for the corresponding
%       dimension. Otherwise, each vector will contain one element for each
%       scan point. The number of coordinate vectors is variable and should
%       be at equal to or higher than the index of the highest nonzero
%       dimension used in the scan.
%   f - Vector of frequencies.
%   Data - If the data is uniform, Data(i1, i2, ..., ff, cc) will be equal
%       to the measurement made at coordinate (x(i0), y(i1), ...) when
%       using a frequency of f(ff) and using channel cc. The size of Data
%       depends on the number of output parameters specified. For example,
%       calling as [x, y, f, Data, Header] = importScan(...) will result in
%       Data being (numX by numY by numF by numChannels).
%       If the data is nonuniform, Data will be (numPoints by numF by
%       numChannels), and Data(ii, ff, cc) will be the measurement made at
%       coordinate (x(ii), y(ii), ...).
%   Header - Structure containing the following fields:
%       .header - String containing user, date, and time information.
%       .description - String describing the scan.
%       .deviceName - String describing the measurement device used.
%       .channelNames - Array of strings giving the name of each channel.
%       .namedArguments - Struct containing name value pairs of arguments
%           contained in the scan description. Any text of the form
%           {name = value} or {name : value} will be captured. The name
%           parameters will be lowercase and have all spaces replaced with
%           underscores. The value parameters will be strings.
%
% Author: Matt Dvorsky

arguments
    filenameIn(1, 1) string;
end

outputDimensionCount = nargout - 3;

%% Open File
% Add ".scan" extension if filenameIn has no extension.
[path, name, ext] = fileparts(filenameIn);
if (ext == "")
    filename = fullfile(path, strcat(name, ".scan"));
else
    filename = filenameIn;
end

% Don't forget to close the fileHandle whenever returning or throwing.
fileHandle = fopen(filename);
if fileHandle == -1
    error("Scan file '%s' not found.", filename);
end

try
    %% Get Version Info
    % Scan file code is an value contained in the first 8 bytes of the file.
    scanFileCode = fread(fileHandle, 1, "double");
    if scanFileCode ~= 63474328
        error("*.scan file type not recognized.");
    end

    % Currently, there is only 1 version of the scan file format.
    scanFileVersion = fread(fileHandle, 1, "double");
    if scanFileVersion ~= 1
        error("*.scan file version is not supported.");
    end

    %% Read Header Data From Scan File
    Header.header = string(fread(fileHandle, ...
        fread(fileHandle, 1, "double"), "double=>char").');
    Header.description = string(fread(fileHandle, ...
        fread(fileHandle, 1, "double"), "double=>char").');
    Header.deviceName = string(fread(fileHandle, ...
        fread(fileHandle, 1, "double"), "double=>char").');

    isUniform = fread(fileHandle, 1, "double");
    Header.isUniform = isUniform;
    numFileDims = fread(fileHandle, 1, "double");
    dimOrder = 1 + fread(fileHandle, numFileDims, "double");
    dimSize = fread(fileHandle, numFileDims, "double");
    numChannels = fread(fileHandle, 1, "double");

    Header.channelNames = strings(numChannels, 1);
    for ii = 1:numChannels
        Header.channelNames(ii) = (string(fread(...
            fileHandle, fread(fileHandle, 1, "double"), "double=>char").'));
    end

    %% Read Scan Coordinates and Frequencies
    numF = fread(fileHandle, 1, "double");
    isComplex = fread(fileHandle, 1, "double");

    axisCoordinates = cell(numFileDims, 1);
    if isUniform
        % In the uniform case, numSteps(n) will contain the size of the nth
        % dimension. The file will contain numSteps(n) data points for each
        % dimension, specifying the relative coordinates of each uniform grid.
        % Then, the absolute coordinates are specified in the same way. The
        % absolute coordinates are currently ignored.
        for ii = 1:numFileDims  % Get relative location vector.
            axisCoordinates(ii) = {fread(fileHandle, dimSize(ii), "double")};
        end
        fread(fileHandle, sum(dimSize), "double"); % Discard absolute location.
    else
        % In the nonuniform case, numSteps(1) will contain the total number of
        % scan points. The file will contain numSteps(1) data points for each
        % dimension, specifying the relative coordinates of each every scan
        % point grid. Then, the absolute coordinates are specified in the same
        % way. The absolute coordinates are currently ignored.
        for ii = 1:numFileDims  % Get relative location.
            axisCoordinates(ii) = {fread(fileHandle, dimSize(1), "double")};
        end
        fread(fileHandle, dimSize(1) .* numFileDims, "double"); % Discard absolute location.
    end

    % Next, the file contains the vector of frequencies in GHz
    f = fread(fileHandle, numF, "double"); % Read frequency vector

    % If end of file was reached, header is missing data.
    if feof(fileHandle)
        error("Scan file '%s' header is corrupted.", filename);
    end

    %% Read Scan Measurement Data
    numDataPoints = numF .* numChannels .* prod(dimSize);

    % Read data from file.
    numDataPointsToRead = numDataPoints * (1 + isComplex);
    Data = fread(fileHandle, numDataPointsToRead, "double");

    % Check for missing data
    if length(Data) < numDataPointsToRead
        warning(strcat("Scan file '%s' contains (%d) measurement points, ", ...
            "which is less than the (%d) measurement points expected. ", ...
            "Data will be padded with zeros."), ...
            filename, length(Data), numDataPointsToRead);

        % Pad Missing Data With Zeros
        Data = [Data; zeros(numDataPointsToRead - length(Data), 1)];
    end

    % Check for too much data
    fread(fileHandle, 1);
    if ~feof(fileHandle)
        warning(strcat("Scan file '%s' contains more data than expected. ", ...
            "The extra data will be ignored."), filename);
    end

    % Reorganize complex data.
    if isComplex
        % Complex data is partially interleaved real imaginary. Every scan
        % point contains all real data followed by all imaginary data.
        Data = reshape(Data, numF .* numChannels, 2, []);
        Data = complex(Data(:, 1, :), Data(:, 2, :));
    end
catch ex
    fclose(fileID);
    rethrow(ex);
end

% Done with reading data from file.
fclose(fileHandle);

%% Check File Dimensions and Requested Output Dimensions
if outputDimensionCount < numFileDims
    if all(dimSize(outputDimensionCount + 1:end) == 1)
        % In this case, the number of dimensions of Data can be reduced,
        % since the extra dimensions are singleton. We can fix this by
        % removing these elements in dimOrder and dimSize.
        numFileDims = outputDimensionCount;
        dimOrder(dimOrder > outputDimensionCount) = [];
        dimSize = dimSize(1:outputDimensionCount);
    else
        error(strcat("Requested number of output dimensions (%d) is ", ...
            "less than the number of dimensions in the scan file (%d)."), ...
            outputDimensionCount, find(dimSize > 1, 1, "last"));
    end
end

if outputDimensionCount > numFileDims
    warning(strcat("Requested number of output dimensions (%d) is greater ", ...
        "than the number of dimensions in the scan file (%d). ", ...
        "Extra singleton dimensions will be added to the output."), ...
        outputDimensionCount, numFileDims);
end

%% Set Output Coordinates and Frequencies
varargout = cell(outputDimensionCount + 3, 1);

% Set output coordinate vectors to values parsed from scan file.
for ii = 1:numFileDims
    varargout{ii} = axisCoordinates{ii};
end

% Set remaining requested output coordinate vectors to 0.
for ii = (numFileDims + 1):outputDimensionCount
    if isUniform
        varargout{ii} = 0;
    else
        varargout{ii} = zeros(prod(dimSize), 1);
    end
end

%% Reorganize Data
% Set output axis order based on number of requested channels.
% Add additional indices to axis order if needed, and add 1's to the output
% dimensions sizes.
outputDimOrder = [dimOrder; ((numFileDims + 1):outputDimensionCount).'];
outputDimSize = [dimSize; 1 + 0*((numFileDims + 1):outputDimensionCount).'];

Data = reshape(Data, numF, numChannels, []);
if isUniform
    % Flip every other row, column, etc., to account for raster scan.
    for ii = 1:(numFileDims - 1)
        Data = reshape(Data, numF, numChannels, ...
            prod(outputDimSize(outputDimOrder(1:ii-1))), ...
            outputDimSize(outputDimOrder(ii)), []);
        Data(:, :, :, :, 2:2:end) = flip(Data(:, :, :, :, 2:2:end), 4);
    end

    Data = reshape(Data, [numF; numChannels; ...
        outputDimSize(outputDimOrder)].');

    % Permute so dimensions are (a1, a2, ... , f, Channel)
    Data = ipermute(Data, [length(outputDimOrder) + [1; 2]; ...
        outputDimOrder]);
else
    % Permute so dimensions are (Scan Location, f, Channel)
    Data = permute(Data, [3, 1, 2]);
end

%% Parse Scan Header Description Named Arguments
% Parse Header.description for all named value pairs.
% The following regex string matches {name = val} or {name : val}, and
% captures (name) and (val), removing any surrounding whitespace.
regexpSearchString = "{\s*(.+?)\s*[=:]\s*(.+?)\s*}";

% Search for all name value pairs
nameValuePairs = regexp(Header.description, regexpSearchString, "tokens");

% Add pairs to struct, removing spaces and capitalization from all names.
fields = struct();
for ii = 1:length(nameValuePairs)
    try
        fields.(strrep(lower(nameValuePairs{ii}(1)), " ", "_")) = ...
            nameValuePairs{ii}(2);
    catch
        warning(strcat("Unable to assign field name '%s' and its ", ...
            "corresponding value '%s' to the nameArguments struct."), ...
            nameValuePairs{ii}(1), nameValuePairs{ii}(2));
    end
end
Header.namedArguments = fields;

%% Set Remaining Outputs
varargout{outputDimensionCount + 1} = f;
varargout{outputDimensionCount + 2} = Data;
varargout{outputDimensionCount + 3} = Header;

end