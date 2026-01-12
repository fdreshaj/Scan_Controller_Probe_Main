function [] = hdf5ToScan_matlab(hdf5FileName, scanFileName)
%HDF5TOSCAN_MATLAB Convert HDF5 file to .scan format (MATLAB version)

arguments
    hdf5FileName(1, 1) string = "";
    scanFileName(1, 1) string = "";
end

%% Select input file if not provided
if hdf5FileName == ""
    [file, path] = uigetfile('*.hdf5', 'Select the HDF5 File to Convert');
    if isequal(file, 0)
        fprintf('File selection cancelled.\n');
        return;
    end
    hdf5FileName = fullfile(path, file);
end

%% Read HDF5 file - FAST VERSION
fprintf('Reading HDF5 file: %s\n', hdf5FileName);

% Read frequency and coordinate data
F = h5read(hdf5FileName, '/Frequencies/Range');
X_vec = h5read(hdf5FileName, '/Coords/x_data');
Y_vec = h5read(hdf5FileName, '/Coords/y_data');
Z_vec = h5read(hdf5FileName, '/Coords/z_data');

% Ensure coordinates are real doubles
X_vec = double(real(X_vec(:)));
Y_vec = double(real(Y_vec(:)));
Z_vec = double(real(Z_vec(:)));
F = double(real(F(:)));

% Get metadata - handle both string and numeric formats
try
    wasUniform_raw = h5readatt(hdf5FileName, '/', 'wasUniform');
    if iscell(wasUniform_raw)
        % Stored as string, convert
        wasUniform = strcmpi(wasUniform_raw{1}, 'true') || strcmpi(wasUniform_raw{1}, '1');
    elseif ischar(wasUniform_raw)
        % Stored as char array
        wasUniform = strcmpi(wasUniform_raw, 'true') || strcmpi(wasUniform_raw, '1');
    else
        % Stored as number
        wasUniform = logical(wasUniform_raw);
    end
catch
    % If attribute doesn't exist, try to detect
    tol = 1e-9;
    uniqueX = uniquetol(X_vec, tol);
    uniqueY = uniquetol(Y_vec, tol);
    uniqueZ = uniquetol(Z_vec, tol);
    wasUniform = (length(uniqueX) * length(uniqueY) * max(1, length(uniqueZ)) == length(X_vec));
    fprintf('  wasUniform attribute not found, auto-detected as: %d\n', wasUniform);
end

try
    isComplexData_raw = h5readatt(hdf5FileName, '/', 'isComplex');
    if iscell(isComplexData_raw)
        isComplexData = strcmpi(isComplexData_raw{1}, 'true') || strcmpi(isComplexData_raw{1}, '1');
    elseif ischar(isComplexData_raw)
        isComplexData = strcmpi(isComplexData_raw, 'true') || strcmpi(isComplexData_raw, '1');
    else
        isComplexData = logical(isComplexData_raw);
    end
catch
    isComplexData = true; % Assume complex if not specified
    fprintf('  isComplex attribute not found, assuming: %d\n', isComplexData);
end

numPoints = length(X_vec);
numFreqs = length(F);

fprintf('  Points: %d\n', numPoints);
fprintf('  Frequencies: %d\n', numFreqs);
fprintf('  Was uniform: %d\n', wasUniform);
fprintf('  Is complex: %d\n', isComplexData);

% Read ALL data at once
if isComplexData
    S11_real = h5read(hdf5FileName, '/Data/S21_real');
    S11_imag = h5read(hdf5FileName, '/Data/S21_imag');
    allData = complex(S11_real, S11_imag);
else
    allData = h5read(hdf5FileName, '/Data/S21');
end

% Check dimensions and transpose if needed
fprintf('  Raw data size: %s\n', mat2str(size(allData)));
if size(allData, 1) == numFreqs && size(allData, 2) == numPoints
    % Data is (numFreqs × numPoints), need to transpose
    allData = allData.';
    fprintf('  Transposed data to: %s\n', mat2str(size(allData)));
elseif size(allData, 1) ~= numPoints || size(allData, 2) ~= numFreqs
    error('Data dimensions do not match expected size (%d × %d)', numPoints, numFreqs);
end

fprintf('  Data loaded\n');

%% Reconstruct scan format
if wasUniform
    % Detect grid structure
    tol = 1e-9;
    uniqueX = uniquetol(X_vec, tol);
    uniqueY = uniquetol(Y_vec, tol);
    uniqueZ = uniquetol(Z_vec, tol);
    
    uniqueX = sort(uniqueX);
    uniqueY = sort(uniqueY);
    uniqueZ = sort(uniqueZ);
    
    numX = length(uniqueX);
    numY = length(uniqueY);
    numZ = length(uniqueZ);
    
    fprintf('  Grid dimensions: %d × %d', numX, numY);
    if numZ > 1
        fprintf(' × %d', numZ);
    end
    fprintf('\n');
    
    % Reshape data to grid
    if numZ == 1
        % 2D scan
        Data = zeros(numX, numY, numFreqs, 1);
        
        for ii = 1:numPoints
            [~, ix] = min(abs(uniqueX - X_vec(ii)));
            [~, iy] = min(abs(uniqueY - Y_vec(ii)));
            
            Data(ix, iy, :, 1) = allData(ii, :);
        end
        
        axisCoordinates = {uniqueX(:), uniqueY(:)};
    else
        % 3D scan
        Data = zeros(numX, numY, numZ, numFreqs, 1);
        
        for ii = 1:numPoints
            [~, ix] = min(abs(uniqueX - X_vec(ii)));
            [~, iy] = min(abs(uniqueY - Y_vec(ii)));
            [~, iz] = min(abs(uniqueZ - Z_vec(ii)));
            
            Data(ix, iy, iz, :, 1) = allData(ii, :);
        end
        
        axisCoordinates = {uniqueX(:), uniqueY(:), uniqueZ(:)};
    end
    
    isUniform = true;
else
    % Non-uniform scan
    Data = reshape(allData, [numPoints, numFreqs, 1]);
    axisCoordinates = {X_vec(:), Y_vec(:), Z_vec(:)};
    isUniform = false;
end

%% Create Header
Header.channelNames = ["S11"];
try
    Header.description = string(h5readatt(hdf5FileName, '/', 'description'));
catch
    Header.description = "Imported from HDF5";
end
try
    Header.deviceName = string(h5readatt(hdf5FileName, '/', 'deviceName'));
catch
    Header.deviceName = "HDF5 Import";
end
Header.header = sprintf("Converted from HDF5 on %s", datestr(now));

%% Generate output filename
if scanFileName == ""
    [path, name, ~] = fileparts(hdf5FileName);
    scanFileName = fullfile(path, [name '.scan']);
end

%% Export
fprintf('\nExporting to .scan file...\n');
exportScan(scanFileName, axisCoordinates, F, Data, Header, IsUniform=isUniform);

fprintf('Successfully exported to: %s\n', scanFileName);

end