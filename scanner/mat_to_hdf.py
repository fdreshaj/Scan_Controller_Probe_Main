#!/usr/bin/env python3
"""
Convert .scan files to HDF5 format
Compatible with the VNA scanner HDF5 structure
"""

import h5py
import numpy as np
import struct
import argparse
import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def read_string(f):
    """Read a string from .scan file (length + chars as doubles)"""
    length_data = f.read(8)
    if len(length_data) < 8:
        return ""  # Return empty string if incomplete
    length = int(struct.unpack('d', length_data)[0])
    chars = []
    for _ in range(length):
        char_data = f.read(8)
        if len(char_data) < 8:
            break  # Stop reading if incomplete
        chars.append(int(struct.unpack('d', char_data)[0]))
    return bytes(chars).decode('utf-8', errors='ignore')


def scan_to_hdf5(scan_path, hdf5_path=None):
    """
    Convert .scan file to HDF5 format
    
    Parameters:
    -----------
    scan_path : str
        Path to input .scan file
    hdf5_path : str, optional
        Path to output HDF5 file (defaults to same name with .hdf5 extension)
    """
    
    with open(scan_path, 'rb') as f:
        
        # Read and verify file code
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        scan_file_code = struct.unpack('d', data)[0]
        if scan_file_code != 63474328:
            raise ValueError("Invalid .scan file format")
        
        # Read version
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        scan_file_version = struct.unpack('d', data)[0]
        if scan_file_version != 1:
            raise ValueError(f"Unsupported .scan file version: {scan_file_version}")
        
        # Read header information
        header = read_string(f)
        description = read_string(f)
        device_name = read_string(f)
        
        # Read scan structure
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        is_uniform = bool(struct.unpack('d', data)[0])
        
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        num_dims = int(struct.unpack('d', data)[0])
        
        data = f.read(8 * num_dims)
        if len(data) < 8 * num_dims:
            raise ValueError("Invalid .scan file format")
        dim_order = [int(x) for x in struct.unpack(f'{num_dims}d', data)]
        
        data = f.read(8 * num_dims)
        if len(data) < 8 * num_dims:
            raise ValueError("Invalid .scan file format")
        dim_size = [int(x) for x in struct.unpack(f'{num_dims}d', data)]
        
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        num_channels = int(struct.unpack('d', data)[0])
        
        # Read channel names
        channel_names = []
        for _ in range(num_channels):
            channel_names.append(read_string(f))
        
        # Read frequency info
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        num_freqs = int(struct.unpack('d', data)[0])
        
        data = f.read(8)
        if len(data) < 8:
            raise ValueError("Invalid .scan file format")
        is_complex = bool(struct.unpack('d', data)[0])
        
        # Read coordinates
        if is_uniform:
            # Read relative coordinates
            data = f.read(8 * dim_size[0])
            if len(data) < 8 * dim_size[0]:
                raise ValueError("Invalid .scan file format")
            x_coords = list(struct.unpack(f'{dim_size[0]}d', data))
            
            data = f.read(8 * dim_size[1])
            if len(data) < 8 * dim_size[1]:
                raise ValueError("Invalid .scan file format")
            y_coords = list(struct.unpack(f'{dim_size[1]}d', data))
            
            # Skip absolute coordinates
            skip_bytes = 8 * sum(dim_size)
            data = f.read(skip_bytes)
            
            # Create full coordinate arrays
            num_points = dim_size[0] * dim_size[1]
            x_data = np.zeros(num_points)
            y_data = np.zeros(num_points)
            
            # Fill in grid coordinates (accounting for raster pattern)
            idx = 0
            for j in range(dim_size[1]):
                for i in range(dim_size[0]):
                    if j % 2 == 0:  # Even rows go forward
                        x_data[idx] = x_coords[i]
                    else:  # Odd rows go backward
                        x_data[idx] = x_coords[dim_size[0] - 1 - i]
                    y_data[idx] = y_coords[j]
                    idx += 1
        else:
            # Read relative coordinates for all points
            num_points = dim_size[0]
            
            data = f.read(8 * num_points)
            if len(data) < 8 * num_points:
                raise ValueError("Invalid .scan file format")
            x_data = np.array(struct.unpack(f'{num_points}d', data))
            
            data = f.read(8 * num_points)
            if len(data) < 8 * num_points:
                raise ValueError("Invalid .scan file format")
            y_data = np.array(struct.unpack(f'{num_points}d', data))
            
            # Skip absolute coordinates
            skip_bytes = 8 * num_points * num_dims
            data = f.read(skip_bytes)
        
        z_data = np.zeros(num_points)  # Assume z = 0
        
        # Read frequencies (they are in GHz in .scan format)
        data = f.read(8 * num_freqs)
        if len(data) < 8 * num_freqs:
            raise ValueError("Invalid .scan file format")
        frequencies_ghz = np.array(struct.unpack(f'{num_freqs}d', data))
        
        # Convert GHz to Hz for HDF5 storage
        frequencies_hz = frequencies_ghz * 1e9
        
        print(f"Debug - Reading frequencies from .scan:")
        print(f"  First freq: {frequencies_ghz[0]:.6f} GHz = {frequencies_hz[0]:.6e} Hz")
        print(f"  Last freq: {frequencies_ghz[-1]:.6f} GHz = {frequencies_hz[-1]:.6e} Hz")
        
        # Read measurement data
        data_array = np.zeros((num_points, num_freqs, num_channels), dtype=complex)
        
        if is_complex:
            # Data is interleaved per point: all real, then all imaginary
            for point_idx in range(num_points):
                # Read real parts
                real_data = []
                for _ in range(num_freqs * num_channels):
                    data = f.read(8)
                    if len(data) < 8:
                        # File ended early, pad with zeros and continue
                        print(f"Warning: Incomplete data at point {point_idx}, padding remaining points with zeros")
                        break
                    real_data.append(struct.unpack('d', data)[0])
                
                if len(real_data) < num_freqs * num_channels:
                    # Pad with zeros and stop reading further points
                    break
                
                # Read imaginary parts
                imag_data = []
                for _ in range(num_freqs * num_channels):
                    data = f.read(8)
                    if len(data) < 8:
                        # File ended early, pad with zeros and continue
                        print(f"Warning: Incomplete data at point {point_idx}, padding remaining points with zeros")
                        break
                    imag_data.append(struct.unpack('d', data)[0])
                
                if len(imag_data) < num_freqs * num_channels:
                    # Pad with zeros and stop reading further points
                    break
                
                # Reshape and assign
                real_arr = np.array(real_data).reshape(num_freqs, num_channels)
                imag_arr = np.array(imag_data).reshape(num_freqs, num_channels)
                data_array[point_idx, :, :] = real_arr + 1j * imag_arr
        else:
            # Real data only
            for point_idx in range(num_points):
                for freq_idx in range(num_freqs):
                    for chan_idx in range(num_channels):
                        data = f.read(8)
                        if len(data) < 8:
                            # File ended early, pad with zeros and continue
                            print(f"Warning: Incomplete data at point {point_idx}, padding remaining points with zeros")
                            break
                        val = struct.unpack('d', data)[0]
                        data_array[point_idx, freq_idx, chan_idx] = val
    
    # Determine output filename
    if hdf5_path is None:
        hdf5_path = Path(scan_path).with_suffix('.hdf5')
    
    # Write HDF5 file
    with h5py.File(hdf5_path, 'w') as hf:
        
        # Parse metadata from description
        # Look for {key = value} or {key : value} patterns
        metadata = {}
        pattern = r'\{\s*(.+?)\s*[=:]\s*(.+?)\s*\}'
        matches = re.findall(pattern, description)
        for key, value in matches:
            metadata[key.strip()] = value.strip()
        
        # Write metadata as attributes
        hf.attrs['header'] = header
        hf.attrs['description'] = description
        hf.attrs['device'] = device_name
        hf.attrs['Units'] = 'Hz'
        for key, value in metadata.items():
            hf.attrs[key] = value
        
        # Create groups
        hf.create_group("/Frequencies")
        hf.create_group("/Point_Data")
        hf.create_group("/Coords")
        
        # Write frequency data
        hf.create_dataset("/Frequencies/Range", data=frequencies_hz)
        
        # Write coordinate data
        hf.create_dataset("/Coords/x_data", data=x_data)
        hf.create_dataset("/Coords/y_data", data=y_data)
        hf.create_dataset("/Coords/z_data", data=z_data)
        
        # Write point data
        # Undo raster pattern if uniform to get original scan order
        if is_uniform:
            data_grid = data_array.reshape(dim_size[1], dim_size[0], num_freqs, num_channels)
            # Flip alternate rows back
            data_grid[1::2, :, :, :] = data_grid[1::2, ::-1, :, :]
            data_corrected = data_grid.reshape(-1, num_freqs, num_channels)
        else:
            data_corrected = data_array
        
        for i in range(num_points):
            point_name = f"Point_{i}"
            hf.create_dataset(f"/Point_Data/{point_name}", data=data_corrected[i, :, :])
        
        # Store channel information
        hf.attrs['channel_names'] = ','.join(channel_names)
        hf.attrs['num_channels'] = num_channels
    
    print(f"Successfully converted {scan_path} to {hdf5_path}")
    print(f"  Points: {num_points}")
    print(f"  Frequencies: {num_freqs} (range: {frequencies_hz[0]:.2e} to {frequencies_hz[-1]:.2e} Hz)")
    print(f"  Channels: {num_channels}")
    print(f"  Channel names: {', '.join(channel_names)}")
    print(f"  Uniform: {is_uniform}")
    print(f"\nHDF5 Structure:")
    print(f"  /Frequencies/Range: {frequencies_hz.shape}")
    print(f"  /Coords/x_data: {x_data.shape}")
    print(f"  /Coords/y_data: {y_data.shape}")
    print(f"  /Point_Data/Point_N: {num_points} datasets of shape {data_corrected[0].shape}")
    
    return hdf5_path


def run_gui():
    """Run the GUI version of the converter"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Ask user to select input .scan file
    scan_path = filedialog.askopenfilename(
        title="Select .scan file to convert",
        filetypes=[("Scan files", "*.scan"), ("All files", "*.*")]
    )
    
    if not scan_path:
        print("No file selected. Exiting.")
        return
    
    # Ask user where to save the HDF5 file
    default_hdf5 = str(Path(scan_path).with_suffix('.hdf5'))
    hdf5_path = filedialog.asksaveasfilename(
        title="Save HDF5 file as",
        initialfile=Path(default_hdf5).name,
        defaultextension=".hdf5",
        filetypes=[("HDF5 files", "*.hdf5 *.h5"), ("All files", "*.*")]
    )
    
    if not hdf5_path:
        print("No output file selected. Exiting.")
        return
    
    try:
        output_path = scan_to_hdf5(scan_path, hdf5_path)
        messagebox.showinfo("Success", f"Successfully converted to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert .scan to HDF5 format')
    parser.add_argument('input', nargs='?', help='Input .scan file (optional if using GUI)')
    parser.add_argument('-o', '--output', help='Output HDF5 file (optional)')
    parser.add_argument('--gui', action='store_true', help='Use GUI file picker')
    
    args = parser.parse_args()
    
    # If no input file provided or --gui flag used, run GUI
    if args.input is None or args.gui:
        run_gui()
    else:
        scan_to_hdf5(args.input, args.output)