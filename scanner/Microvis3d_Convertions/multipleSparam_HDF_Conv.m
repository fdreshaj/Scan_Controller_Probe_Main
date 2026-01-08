function [] = multiSparam_hdf5ToScan_matlab(hdf5FileName, scanFileName)
% HDF5TOSCAN_MATLAB Convert HDF5 file to .scan format with auto-channel detection

arguments
    hdf5FileName(1, 1) string = "";
    scanFileName(1, 1) string = "";
end

%% Select input file
if hdf5FileName == ""
    [file, path] = uigetfile('*.hdf5', 'Select the HDF5 File to Convert');
    if isequal(file, 0), return; end
    hdf5FileName = fullfile(path, file);
end

%% 1. Automatically Detect Channels (S-Parameters)
fprintf('Inspecting HDF5 structure: %s\n', hdf5FileName);
info = h5info(hdf5FileName, '/Data');
datasetNames = {info.Datasets.Name};

% Identify unique base names (e.g., "S11" from "S11_real" and "S11_imag")
% This regex removes the _real/_imag suffix to find the core channel name
baseChannelNames = unique(regexprep(datasetNames, '_real|_imag', ''));
numChannels = length(baseChannelNames);

fprintf('  Found %d channels: %s\n', numChannels, strjoin(baseChannelNames, ', '));

%% 2. Read Coordinates and Metadata
% (Logic derived from)
F = double(real(h5read(hdf5FileName, '/Frequencies/Range')));
X_vec = double(real(h5read(hdf5FileName, '/Coords/x_data')));
Y_vec = double(real(h5read(hdf5FileName, '/Coords/y_data')));
Z_vec = double(real(h5read(hdf5FileName, '/Coords/z_data')));

% Determine uniformity and complexity (Logic from)
try
    isComplexData = logical(h5readatt(hdf5FileName, '/', 'isComplex'));
catch
    isComplexData = any(contains(datasetNames, '_real')); 
end

try
    wasUniform = logical(h5readatt(hdf5FileName, '/', 'wasUniform'));
catch
    wasUniform = (length(uniquetol(X_vec, 1e-9)) * length(uniquetol(Y_vec, 1e-9)) == length(X_vec));
end

numPoints = length(X_vec);
numFreqs = length(F);

%% 3. Load Multi-Channel Data
% Pre-allocate list to hold data for each S-parameter
channelDataList = cell(1, numChannels);

for ch = 1:numChannels
    sName = baseChannelNames{ch};
    if isComplexData
        r = h5read(hdf5FileName, sprintf('/Data/%s_real', sName));
        i = h5read(hdf5FileName, sprintf('/Data/%s_imag', sName));
        tempData = complex(r, i);
    else
        tempData = h5read(hdf5FileName, sprintf('/Data/%s', sName));
    end
    
    % Standardize to (numPoints x numFreqs)
    if size(tempData, 1) == numFreqs && size(tempData, 2) == numPoints
        tempData = tempData.';
    end
    channelDataList{ch} = tempData;
end

%% 4. Reconstruct Scan Format
if wasUniform
    % Grid detection (Logic from)
    uniqueX = sort(uniquetol(X_vec, 1e-9));
    uniqueY = sort(uniquetol(Y_vec, 1e-9));
    uniqueZ = sort(uniquetol(Z_vec, 1e-9));
    numX = length(uniqueX); numY = length(uniqueY); numZ = length(uniqueZ);
    
    if numZ <= 1
        % 2D Scan: Data dimensions (X, Y, Freq, Channel)
        Data = zeros(numX, numY, numFreqs, numChannels);
        for ch = 1:numChannels
            currCh = channelDataList{ch};
            for ii = 1:numPoints
                [~, ix] = min(abs(uniqueX - X_vec(ii)));
                [~, iy] = min(abs(uniqueY - Y_vec(ii)));
                Data(ix, iy, :, ch) = currCh(ii, :);
            end
        end
        axisCoordinates = {uniqueX(:), uniqueY(:)};
    else
        % 3D Scan: Data dimensions (X, Y, Z, Freq, Channel)
        Data = zeros(numX, numY, numZ, numFreqs, numChannels);
        for ch = 1:numChannels
            currCh = channelDataList{ch};
            for ii = 1:numPoints
                [~, ix] = min(abs(uniqueX - X_vec(ii)));
                [~, iy] = min(abs(uniqueY - Y_vec(ii)));
                [~, iz] = min(abs(uniqueZ - Z_vec(ii)));
                Data(ix, iy, iz, :, ch) = currCh(ii, :);
            end
        end
        axisCoordinates = {uniqueX(:), uniqueY(:), uniqueZ(:)};
    end
else
    % Non-uniform: Data dimensions (Points, Freq, Channel)
    Data = zeros(numPoints, numFreqs, numChannels);
    for ch = 1:numChannels
        Data(:,:,ch) = channelDataList{ch};
    end
    axisCoordinates = {X_vec(:), Y_vec(:), Z_vec(:)};
end

%% 5. Export with Dynamic Header
Header.channelNames = string(baseChannelNames);
Header.description = "Multi-channel import";
Header.deviceName = "HDF5 Auto-Explorer";
Header.header = sprintf("Converted on %s", datestr(now));

if scanFileName == ""
    [p, n, ~] = fileparts(hdf5FileName);
    scanFileName = fullfile(p, [n '.scan']);
end

exportScan(scanFileName, axisCoordinates, F, Data, Header, IsUniform=wasUniform);
fprintf('Successfully exported %d channels to: %s\n', numChannels, scanFileName);

end