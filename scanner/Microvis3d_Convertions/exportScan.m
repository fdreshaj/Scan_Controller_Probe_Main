function [] = exportScan(filenameIn, axisCoordinates, f, Data, HeaderIn, options)
%Export a ".scan" file like that created by the CNDE scanner program.
% This function exports and parses a ".scan" file. This is a custom file
% format that is used by the CNDE scan-controller program.
%
% Example Usage:
%   % Uniform (gridded) scan.
%   exportScan(filename, {x}, f, Data, Header);     % 1D scan.
%   exportScan(filename, {x, y}, f, Data, Header);  % 2D scan.
%   exportScan(filename, {x, y, z, w, ...}, f, Data, Header);   % ND scan.
%
%   % Non-uniform scan.
%   exportScan(filename, axisCoordinates, f, Data, Header, IsUniform=false);
%
%
% Inputs:
%   filenameIn - Path to the output file. If the file has no extension,
%       ".scan" will be automatically appended.
%   axisCoordinates - Cell array containing the coordinates of each
%       dimension. For uniform data, numel(axisCoordinates{ii}) should be
%       equal to size(Data, ii), and each should be uniformly-increasing
%       when put in column order. For nonuniform data,
%       numel(axisCoordinates{ii}) should be equal tof size(Data, 1) for
%       all ii.
%   f - Vector of frequencies in GHz.
%   Data - The value of Data(i1, i2, ..., ff, cc) should be equal to the
%       measurement made at coordinate (x(i0), y(i1), ...) when using a
%       frequency of f(ff) and using channel cc. The size of Data should
%       match the lengths of each element axisCoordinates.
%       If the data is nonuniform, Data should be (numPoints by numF by
%       numChannels), and Data(ii, ff, cc) should be the measurement made
%       at coordinate (x(ii), y(ii), ...).
%   Header (optional) - Structure containing all or some of the following fields:
%       .header - String containing user, date, and time information.
%       .description - String describing the scan.
%       .deviceName - String describing the measurement device used.
%       .channelNames - Array of strings giving the name of each channel.
%
% Named Arguments:
%   IsUniform (true) - Boolean specifying whether the data is uniform.
%
% Author: Matt Dvorsky

arguments
    filenameIn(1, 1) string;
    axisCoordinates cell {mustBeNonempty};
    f(:, 1) double {mustBePositive, mustBeFinite, mustBeNonempty};
    Data double;
    HeaderIn(1, 1) = struct();

    options.IsUniform(1, 1) logical = 1;
end

%% Check Input Sizes and Determine Header Parameters
numDims = numel(axisCoordinates);
dimSize(:, 1) = cellfun(@numel, axisCoordinates);
isUniform = options.IsUniform;

if isUniform
    if ~all(dimSize == size(Data, 1:numDims).')
        error(strcat("Inconsistent dimension sizes. The first (%d) dimensions ", ...
            "of Data do not match the lengths of axisCoordinates."), numDims);
    end
    if numel(f) ~= size(Data, numDims + 1)
        error(strcat("Inconsistent dimension sizes. The dimension (%d) ", ...
            "of Data does not match length(f)."), numDims + 1);
    end
    if ndims(Data) > (numDims + 2)
        error(strcat("Number of dimensions for Data should no greater than ", ...
            "(%d), but is currently (%d)."), numDims + 2, ndims(Data));
    end

    numChannels = size(Data, numDims + 2);
else
    if ~all(dimSize == size(Data, 1))
        error(strcat("Inconsistent dimension sizes. The lengths of ", ...
            "axisCoordinates do not match the first dimension of Data."));
    end
    if numel(f) ~= size(Data, 2)
        error(strcat("Inconsistent dimension sizes. The 2nd dimension ", ...
            "of Data does not match length(f)."));
    end
    if ndims(Data) > 3
        error(strcat("Number of dimensions for Data should no greater than ", ...
            "(%d), but is currently (%d)."), 3, ndims(Data));
    end

    dimSize(2:end) = 1;
    numChannels = size(Data, 3);
end

numF = length(f);
dimOrder = (1:numDims).';
isComplex = ~isreal(Data);

%% Validate Header
if isfield(HeaderIn, "header")
    Header.header = string(HeaderIn.header(1));
else
    Header.header = "";
end

if isfield(HeaderIn, "description")
    Header.description = string(HeaderIn.description(1));
else
    Header.description = "";
end

if isfield(HeaderIn, "deviceName")
    Header.deviceName = string(HeaderIn.deviceName(1));
else
    Header.deviceName = "";
end

if isfield(HeaderIn, "channelNames")
    Header.channelNames = string(HeaderIn.channelNames(:));
else
    Header.channelNames = [];
end

if length(Header.channelNames) < numChannels
    warning(strcat("Header.channelNames only contains (%d) elements, ", ...
        "but should contain (%d). Default names will be used."), ...
        length(Header.channelNames), numChannels);
    Header.channelNames = [Header.channelNames; compose("Channel %d", ...
        (length(Header.channelNames) + 1:numChannels).')];
elseif length(Header.channelNames) > numChannels
    warning(strcat("Header.channelNames contains too many elements. ", ...
        "Extra elements will be ignored."));
end

%% Scan File Definition
scanFileCode = 63474328;
scanFileVersion = 1;

%% Open File
% Add ".scan" extension if filenameIn has no extension.
[path, name, ext] = fileparts(filenameIn);
if (ext == "")
    filename = fullfile(path, strcat(name, ".scan"));
else
    filename = filenameIn;
end

fileHandle = fopen(filename, "w");
if fileHandle == -1
    error("Could not write to file '%s'.", filename);
end
try
    %% Write Version Info
    % Scan file code is an value contained in the first 8 bytes of the file.
    fwrite(fileHandle, scanFileCode, "double");
    fwrite(fileHandle, scanFileVersion, "double");

    %% Write Scan File Header
    % Size and data for header, description, and deviceName
    fwrite(fileHandle, strlength(Header.header), "double");
    fwrite(fileHandle, char(Header.header), "double");
    fwrite(fileHandle, strlength(Header.description), "double");
    fwrite(fileHandle, char(Header.description), "double");
    fwrite(fileHandle, strlength(Header.deviceName), "double");
    fwrite(fileHandle, char(Header.deviceName), "double");

    % Scan data format and sizes
    fwrite(fileHandle, isUniform, "double");
    fwrite(fileHandle, numDims, "double");
    fwrite(fileHandle, dimOrder - 1, "double");
    fwrite(fileHandle, dimSize, "double");
    fwrite(fileHandle, numChannels, "double");

    % Channel Names
    for ii = 1:numChannels
        fwrite(fileHandle, strlength(Header.channelNames(ii)), "double");
        fwrite(fileHandle, char(Header.channelNames(ii)), "double");
    end

    %% Write Scan Coordinates and Frequencies
    fwrite(fileHandle, numF, "double");
    fwrite(fileHandle, isComplex, "double");

    % Relative location
    for ii = 1:numDims
        fwrite(fileHandle, axisCoordinates{ii}, "double");
    end
    % Absolute location. Same as relative location for now.
    for ii = 1:numDims
        fwrite(fileHandle, axisCoordinates{ii}, "double");
    end

    % Frequency vector
    fwrite(fileHandle, f, "double");

    %% Write Measurement Data
    % Permute scan data dimensions to match expected format.
    if isUniform
        % Expects (f, channel, x, y, ...)
        Data = permute(Data, [[1; 2] + numDims; dimOrder]);
    else
        % Expects (f, channel, coord)
        Data = permute(Data, [2, 3, 1]);
    end

    % Format scan data into raster scan format if uniform.
    if isUniform
        % Flip every other row, column, etc., to account for raster scan.
        for ii = 1:(numDims - 1)
            Data = reshape(Data, numF, numChannels, ...
                prod(dimSize(dimOrder(1:ii-1))), dimSize(dimOrder(ii)), []);
            Data(:, :, :, :, 2:2:end) = flip(Data(:, :, :, :, 2:2:end), 4);
        end
    end

    % Separate real and imaginary if complex.
    if isComplex
        Data = cat(2, real(Data), imag(Data));
    end

    % Write Data to file.
    fwrite(fileHandle, Data, "double");
catch ex
    fclose(fileHandle);
    rethrow(ex);
end

% Close file handle.
fclose(fileHandle);

end