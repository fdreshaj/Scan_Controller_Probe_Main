#!/usr/bin/env python3
"""
Convert .scan file to HDF5 format matching CNDE structure.

This script converts .scan files to HDF5 format with complex number support
using compound datatypes (struct with 'r' and 'i' fields).

Usage:
    python scan_to_hdf5.py
    python scan_to_hdf5.py input.scan
    python scan_to_hdf5.py input.scan output.hdf5

Author: Assistant
"""

import numpy as np
import h5py
import struct
import sys
import os
from pathlib import Path
from tkinter import Tk, filedialog


def read_scan_file(filename):
    """
    Read a .scan file and return coordinates, frequencies, data, and header.
    
    Returns:
        tuple: (X, Y, Z, f, Data, Header)
    """
    with open(filename, 'rb') as f:
        # Read version info
        scan_file_code = struct.unpack('d', f.read(8))[0]
        if scan_file_code != 63474328:
            raise ValueError("*.scan file type not recognized.")
        
        scan_file_version = struct.unpack('d', f.read(8))[0]
        if scan_file_version != 1:
            raise ValueError("*.scan file version is not supported.")
        
        # Read header
        header_len = int(struct.unpack('d', f.read(8))[0])
        header_str = ''.join(chr(int(x)) for x in struct.unpack(f'{header_len}d', f.read(8*header_len)))
        
        desc_len = int(struct.unpack('d', f.read(8))[0])
        description = ''.join(chr(int(x)) for x in struct.unpack(f'{desc_len}d', f.read(8*desc_len)))
        
        device_len = int(struct.unpack('d', f.read(8))[0])
        device_name = ''.join(chr(int(x)) for x in struct.unpack(f'{device_len}d', f.read(8*device_len)))
        
        # Read scan format
        is_uniform = bool(struct.unpack('d', f.read(8))[0])
        num_dims = int(struct.unpack('d', f.read(8))[0])
        dim_order = [int(x) + 1 for x in struct.unpack(f'{num_dims}d', f.read(8*num_dims))]
        dim_size = [int(x) for x in struct.unpack(f'{num_dims}d', f.read(8*num_dims))]
        num_channels = int(struct.unpack('d', f.read(8))[0])
        
        # Read channel names
        channel_names = []
        for i in range(num_channels):
            name_len = int(struct.unpack('d', f.read(8))[0])
            name = ''.join(chr(int(x)) for x in struct.unpack(f'{name_len}d', f.read(8*name_len)))
            channel_names.append(name)
        
        # Read frequencies and coordinates
        num_f = int(struct.unpack('d', f.read(8))[0])
        is_complex = bool(struct.unpack('d', f.read(8))[0])
        
        # Read axis coordinates
        axis_coords = []
        if is_uniform:
            for i in range(num_dims):
                coords = struct.unpack(f'{dim_size[i]}d', f.read(8*dim_size[i]))
                axis_coords.append(np.array(coords))
            # Skip absolute location
            f.read(8 * sum(dim_size))
        else:
            for i in range(num_dims):
                coords = struct.unpack(f'{dim_size[0]}d', f.read(8*dim_size[0]))
                axis_coords.append(np.array(coords))
            # Skip absolute location
            f.read(8 * dim_size[0] * num_dims)
        
        # Read frequency vector (in GHz)
        freq = np.array(struct.unpack(f'{num_f}d', f.read(8*num_f)))
        
        # Read measurement data
        num_data_points = num_f * num_channels * np.prod(dim_size)
        num_to_read = num_data_points * (1 + is_complex)
        
        # Check remaining file size
        current_pos = f.tell()
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        f.seek(current_pos)  # Seek back
        
        bytes_remaining = file_size - current_pos
        bytes_needed = 8 * num_to_read
        
        if bytes_remaining < bytes_needed:
            print(f"Warning: File appears truncated. Padding with zeros.")
            print(f"  Expected {bytes_needed} bytes ({num_to_read} doubles)")
            print(f"  Only {bytes_remaining} bytes remaining ({bytes_remaining // 8} doubles)")
            
            # Read what we can
            available_doubles = bytes_remaining // 8
            data_bytes = f.read(8 * available_doubles)
            data = np.array(struct.unpack(f'{available_doubles}d', data_bytes))
            
            # Pad with zeros
            data = np.pad(data, (0, num_to_read - available_doubles), mode='constant', constant_values=0)
        else:
            data_bytes = f.read(8 * num_to_read)
            data = np.array(struct.unpack(f'{num_to_read}d', data_bytes))
        
        # Reconstruct complex data
        if is_complex:
            # Data is stored as [real_channels, imag_channels] interleaved
            data = data.reshape(num_f * num_channels, 2, -1)
            real_part = data[:, 0, :]
            imag_part = data[:, 1, :]
            data = (real_part + 1j * imag_part).reshape(num_f, num_channels, -1)
        else:
            data = data.reshape(num_f, num_channels, -1)
        
        # Handle uniform vs non-uniform
        if is_uniform:
            # Reshape to grid dimensions
            data = data.reshape(num_f, num_channels, *dim_size)
            
            # Undo raster scan pattern - flip every other row/column/plane
            for dim_idx in range(num_dims - 1):
                # Get shape for reshaping
                before_dims = dim_size[:dim_idx]
                current_dim = dim_size[dim_idx]
                after_dims = dim_size[dim_idx+1:]
                
                # Reshape to isolate current dimension
                shape = [num_f, num_channels] + list(before_dims) + [current_dim, -1]
                data = data.reshape(shape)
                
                # Flip every other slice along the dimension after current
                data[..., 1::2] = np.flip(data[..., 1::2], axis=len(shape)-2)
            
            # Final reshape back to full grid
            data = data.reshape(num_f, num_channels, *dim_size)
            
            # Transpose to (spatial dims, freq, channels)
            perm = list(range(2, 2 + num_dims)) + [0, 1]
            data = np.transpose(data, perm)
            
            # Create full coordinate arrays
            if num_dims == 2:
                Xgrid, Ygrid = np.meshgrid(axis_coords[0], axis_coords[1], indexing='ij')
                X = Xgrid.flatten()
                Y = Ygrid.flatten()
                Z = np.zeros_like(X)
            elif num_dims == 3:
                Xgrid, Ygrid, Zgrid = np.meshgrid(axis_coords[0], axis_coords[1], axis_coords[2], indexing='ij')
                X = Xgrid.flatten()
                Y = Ygrid.flatten()
                Z = Zgrid.flatten()
            else:
                raise ValueError(f"Unsupported number of dimensions: {num_dims}")
            
            # Reshape data to (points, freq, channels)
            data = data.reshape(-1, num_f, num_channels)
        else:
            # Non-uniform: transpose to (points, freq, channels)
            data = np.transpose(data, [2, 0, 1])
            X = axis_coords[0]
            Y = axis_coords[1] if num_dims > 1 else np.zeros_like(X)
            Z = axis_coords[2] if num_dims > 2 else np.zeros_like(X)
        
        Header = {
            'header': header_str,
            'description': description,
            'deviceName': device_name,
            'channelNames': channel_names,
            'isUniform': is_uniform
        }
        
        return X, Y, Z, freq, data, Header


def scan_to_hdf5(scan_filename, hdf5_filename=None):
    """
    Convert a .scan file to HDF5 format.
    
    Args:
        scan_filename: Path to input .scan file
        hdf5_filename: Path to output HDF5 file (optional)
    """
    print(f"Reading .scan file: {scan_filename}")
    
    # Read scan file
    X, Y, Z, f, Data, Header = read_scan_file(scan_filename)
    
    num_points = len(X)
    num_freqs = len(f)
    num_channels = Data.shape[2]
    
    print(f"  Points: {num_points}")
    print(f"  Frequencies: {num_freqs} ({f.min():.3f} - {f.max():.3f} GHz)")
    print(f"  Channels: {num_channels}")
    
    # Generate output filename if not provided
    if hdf5_filename is None:
        hdf5_filename = str(Path(scan_filename).with_suffix('.hdf5'))
    
    # Delete existing file if it exists
    if os.path.exists(hdf5_filename):
        os.remove(hdf5_filename)
        print(f"  Deleted existing file: {hdf5_filename}")
    
    print("\nWriting HDF5 file...")
    
    # Create HDF5 file
    with h5py.File(hdf5_filename, 'w') as hf:
        # Write frequency data (convert GHz to Hz)
        F_Hz = f * 1e9
        hf.create_dataset('/Frequencies/Range', data=F_Hz)
        
        # Write coordinate data
        hf.create_dataset('/Coords/x_data', data=X)
        hf.create_dataset('/Coords/y_data', data=Y)
        hf.create_dataset('/Coords/z_data', data=Z)
        
        # Define complex datatype (compound type with 'r' and 'i' fields)
        complex_dtype = np.dtype([('r', 'f8'), ('i', 'f8')])
        
        # Determine grid indices for naming
        # Find unique coordinates and create index mapping with tolerance
        tol = 1e-9
        unique_x = np.unique(X)
        unique_y = np.unique(Y)
        unique_z = np.unique(Z)
        
        # Write point data
        print("Writing S11 data for each point...")
        for point_idx in range(num_points):
            # Get grid indices for this point by finding closest unique coordinate
            x_idx = np.argmin(np.abs(unique_x - X[point_idx]))
            y_idx = np.argmin(np.abs(unique_y - Y[point_idx]))
            z_idx = np.argmin(np.abs(unique_z - Z[point_idx]))
            
            # Create point name based on grid indices
            # Format: [x_idx y_idx z_idx] or [x_idx y_idx] for 2D
            if len(unique_z) > 1:
                point_name = f'/Point_Data/[{x_idx} {y_idx} {z_idx}]'
            else:
                point_name = f'/Point_Data/[{x_idx} {y_idx}]'
            
            # Extract S11 data for this point (first channel)
            s11_data = Data[point_idx, :, 0]
            
            # Convert complex data to structured array
            s11_struct = np.zeros(num_freqs, dtype=complex_dtype)
            s11_struct['r'] = np.real(s11_data)
            s11_struct['i'] = np.imag(s11_data)
            
            # Write to HDF5
            hf.create_dataset(f'{point_name}/S11/data', data=s11_struct)
            
            # Progress indicator
            if (point_idx + 1) % 100 == 0:
                print(f"  Wrote {point_idx + 1}/{num_points} points...")
        
        # Write metadata as attributes
        print("Writing metadata...")
        if Header['description']:
            hf.attrs['description'] = Header['description']
        if Header['deviceName']:
            hf.attrs['deviceName'] = Header['deviceName']
        if Header['header']:
            hf.attrs['header'] = Header['header']
        
        hf.attrs['numPoints'] = num_points
        hf.attrs['numFrequencies'] = num_freqs
        hf.attrs['conversion_date'] = np.string_(str(np.datetime64('now')))
    
    file_size = os.path.getsize(hdf5_filename) / 1e6
    print(f"\nConversion complete!")
    print(f"Output file: {hdf5_filename}")
    print(f"  Total points: {num_points}")
    print(f"  Frequencies: {num_freqs}")
    print(f"  File size: {file_size:.2f} MB")


def main():
    """Main function with GUI file selection."""
    if len(sys.argv) > 1:
        # Command line argument provided
        scan_filename = sys.argv[1]
        hdf5_filename = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # GUI file selection
        root = Tk()
        root.withdraw()
        scan_filename = filedialog.askopenfilename(
            title='Select the .scan File to Convert',
            filetypes=[('Scan files', '*.scan'), ('All files', '*.*')]
        )
        root.destroy()
        
        if not scan_filename:
            print("File selection cancelled.")
            return
        
        hdf5_filename = None
    
    scan_to_hdf5(scan_filename, hdf5_filename)


if __name__ == '__main__':
    main()