%% 
function [] = scanToHDF5_matlab(scanFileName, hdf5FileName)
%SCANTOHDF5_MATLAB Convert a .scan file to HDF5 format (MATLAB version)
%
% Usage:
%   scanToHDF5_matlab()                              % GUI file selection
%   scanToHDF5_matlab(scanFileName)                  % Specify input
%   scanToHDF5_matlab(scanFileName, hdf5FileName)    % Specify both

arguments
    scanFileName(1, 1) string = "";
    hdf5FileName(1, 1) string = "";
end

%% Select input file if not provided
if scanFileName == ""
    [file, path] = uigetfile('*.scan', 'Select the .scan File to Convert');
    if isequal(file, 0)
        fprintf('File selection cancelled.\n');
        return;
    end
    scanFileName = fullfile(path, file);
end

%% Import the .scan file
fprintf('Reading .scan file: %s\n', scanFileName);

% Try 3D import first
try
    [X, Y, Z, f, Data, Header] = importScan(scanFileName);
    numDims = 3;
catch
    % If 3D fails, try 2D
    try
        [X, Y, f, Data, Header] = importScan(scanFileName);
        Z = 0;
        numDims = 2;
    catch
        error('Failed to import .scan file. Check file format.');
    end
end

fprintf('  Imported successfully\n');
fprintf('  Dimensions: %s\n', mat2str(size(Data)));
fprintf('  Uniform: %d\n', Header.isUniform);

%% Prepare data based on uniform/non-uniform
if Header.isUniform
    % For uniform scans, flatten to point-based format
    if numDims == 2
        [Xgrid, Ygrid] = ndgrid(X, Y);
        X_vec = Xgrid(:);
        Y_vec = Ygrid(:);
        Z_vec = zeros(size(X_vec));
        
        % Reshape Data from (numX, numY, numF, numCh) to (numPoints, numF, numCh)
        origSize = size(Data);
        numPoints = origSize(1) * origSize(2);
        numFreqs = origSize(3);
        numChannels = size(Data, 4);
        Data = reshape(Data, [numPoints, numFreqs, numChannels]);
    else
        [Xgrid, Ygrid, Zgrid] = ndgrid(X, Y, Z);
        X_vec = Xgrid(:);
        Y_vec = Ygrid(:);
        Z_vec = Zgrid(:);
        
        origSize = size(Data);
        numPoints = origSize(1) * origSize(2) * origSize(3);
        numFreqs = origSize(4);
        numChannels = size(Data, 5);
        Data = reshape(Data, [numPoints, numFreqs, numChannels]);
    end
else
    % Non-uniform: coordinates are already vectors
    X_vec = X(:);
    Y_vec = Y(:);
    Z_vec = Z(:);
    
    numPoints = size(Data, 1);
    numFreqs = size(Data, 2);
    numChannels = size(Data, 3);
end

fprintf('  Points: %d\n', numPoints);
fprintf('  Frequencies: %d\n', numFreqs);
fprintf('  Channels: %d\n', numChannels);

%% Generate output filename if not provided
if hdf5FileName == ""
    [path, name, ~] = fileparts(scanFileName);
    hdf5FileName = fullfile(path, [name '.hdf5']);
end

% Delete existing file if it exists
if isfile(hdf5FileName)
    delete(hdf5FileName);
end

%% Write HDF5 file - FAST VERSION with bulk arrays
fprintf('\nWriting HDF5 file...\n');

% Write frequency data
h5create(hdf5FileName, '/Frequencies/Range', length(f), 'Datatype', 'double');
h5write(hdf5FileName, '/Frequencies/Range', f);

% Write coordinate data
h5create(hdf5FileName, '/Coords/x_data', numPoints, 'Datatype', 'double');
h5write(hdf5FileName, '/Coords/x_data', X_vec);

h5create(hdf5FileName, '/Coords/y_data', numPoints, 'Datatype', 'double');
h5write(hdf5FileName, '/Coords/y_data', Y_vec);

h5create(hdf5FileName, '/Coords/z_data', numPoints, 'Datatype', 'double');
h5write(hdf5FileName, '/Coords/z_data', Z_vec);

% Write ALL data at once as a single 2D array (numPoints × numFreqs)
% Store only first channel for now
S11_data = squeeze(Data(:, :, 1));

if ~isreal(S11_data)
    % Store real and imaginary parts
    h5create(hdf5FileName, '/Data/S11_real', [numPoints, numFreqs], 'Datatype', 'double');
    h5write(hdf5FileName, '/Data/S11_real', real(S11_data));
    
    h5create(hdf5FileName, '/Data/S11_imag', [numPoints, numFreqs], 'Datatype', 'double');
    h5write(hdf5FileName, '/Data/S11_imag', imag(S11_data));
else
    h5create(hdf5FileName, '/Data/S11', [numPoints, numFreqs], 'Datatype', 'double');
    h5write(hdf5FileName, '/Data/S11', S11_data);
end

% Write metadata as attributes
h5writeatt(hdf5FileName, '/', 'numPoints', numPoints);
h5writeatt(hdf5FileName, '/', 'numFrequencies', numFreqs);
h5writeatt(hdf5FileName, '/', 'wasUniform', double(Header.isUniform));
h5writeatt(hdf5FileName, '/', 'isComplex', double(~isreal(S11_data)));
h5writeatt(hdf5FileName, '/', 'conversion_date', datestr(now));

if isfield(Header, 'description') && strlength(Header.description) > 0
    h5writeatt(hdf5FileName, '/', 'description', char(Header.description));
end
if isfield(Header, 'deviceName') && strlength(Header.deviceName) > 0
    h5writeatt(hdf5FileName, '/', 'deviceName', char(Header.deviceName));
end
if isfield(Header, 'header') && strlength(Header.header) > 0
    h5writeatt(hdf5FileName, '/', 'originalHeader', char(Header.header));
end

fprintf('Conversion complete!\n');
fprintf('Output file: %s\n', hdf5FileName);
fprintf('  File size: %.2f MB\n', dir(hdf5FileName).bytes / 1e6);

end