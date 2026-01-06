#!/usr/bin/env python3
"""
Convert HDF5 files to .scan format
Compatible with importScan_MicroVis.m
"""

import h5py
import numpy as np
import struct
import argparse
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox


def write_string(f, s):
    """Write a string to file in .scan format (length + chars as doubles)"""
    s_bytes = s.encode('utf-8')
    f.write(struct.pack('d', len(s_bytes)))
    for byte in s_bytes:
        f.write(struct.pack('d', float(byte)))


def hdf5_to_scan(hdf5_path, scan_path=None, description=""):
    """
    Convert HDF5 file to .scan format
    
    Parameters:
    -----------
    hdf5_path : str
        Path to input HDF5 file
    scan_path : str, optional
        Path to output .scan file (defaults to same name with .scan extension)
    description : str, optional
        Additional description text
    """
    
    # Open HDF5 file
    with h5py.File(hdf5_path, 'r') as hf:
        
        # Read coordinates
        x_data = hf['/Coords/x_data'][:]
        y_data = hf['/Coords/y_data'][:]
        z_data = hf['/Coords/z_data'][:]
        
        # Read frequencies from HDF5 (stored in Hz)
        frequencies_hz = hf['/Frequencies/Range'][:]
        
        # Convert Hz to GHz for .scan format
        frequencies = frequencies_hz / 1e9
        
        print(f"Debug - Frequency conversion:")
        print(f"  From HDF5: {frequencies_hz[0]:.6e} Hz = {frequencies[0]:.6f} GHz")
        print(f"  Last freq: {frequencies_hz[-1]:.6e} Hz = {frequencies[-1]:.6f} GHz")
        print(f"  Num freqs: {len(frequencies)}")
        
        # Read S-parameter data
        point_data_group = hf['/Point_Data']
        point_keys = sorted([k for k in point_data_group.keys() if k.startswith('Point_')])
        
        num_points = len(point_keys)
        num_freqs = len(frequencies)
        
        # Determine number of channels from first point
        first_point = point_data_group[point_keys[0]][:]
        num_channels = first_point.shape[1] if len(first_point.shape) > 1 else 1
        
        # Collect all data
        data = np.zeros((num_points, num_freqs, num_channels), dtype=complex)
        for i, key in enumerate(point_keys):
            point_data = point_data_group[key][:]
            if len(point_data.shape) == 1:
                point_data = point_data.reshape(-1, 1)
            data[i, :, :] = point_data
        
        # Check if scan is uniform (regular grid)
        x_unique = np.unique(x_data)
        y_unique = np.unique(y_data)
        is_uniform = (len(x_unique) * len(y_unique) == num_points)
        
        # Build header information
        header_str = f"User: Python Converter, Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Get metadata from HDF5 attributes
        desc_parts = [description] if description else []
        for key in hf.attrs.keys():
            if key != 'Units':
                desc_parts.append(f"{{{key} = {hf.attrs[key]}}}")
        description_str = " ".join(desc_parts)
        
        device_name = hf.attrs.get('device', 'VNA Scanner')
        
        # Channel names
        channel_names = [f"S{i+1}{i+1}" for i in range(num_channels)]  # Default to S11, S22, etc.
    
    # Determine output filename
    if scan_path is None:
        scan_path = Path(hdf5_path).with_suffix('.scan')
    
    # Write .scan file
    with open(scan_path, 'wb') as f:
        
        # Write file code and version
        f.write(struct.pack('d', 63474328))  # Scan file code
        f.write(struct.pack('d', 1))  # Version
        
        # Write header strings
        write_string(f, header_str)
        write_string(f, description_str)
        write_string(f, str(device_name))
        
        # Determine dimensions
        if is_uniform:
            num_dims = 2  # x and y
            dim_order = np.array([0, 1], dtype=float)  # 0-indexed in file
            dim_size = np.array([len(x_unique), len(y_unique)], dtype=float)
        else:
            num_dims = 2
            dim_order = np.array([0, 1], dtype=float)
            dim_size = np.array([num_points, 1], dtype=float)
        
        # Write scan structure
        f.write(struct.pack('d', 1.0 if is_uniform else 0.0))  # isUniform
        f.write(struct.pack('d', num_dims))
        f.write(struct.pack(f'{len(dim_order)}d', *dim_order))
        f.write(struct.pack(f'{len(dim_size)}d', *dim_size))
        f.write(struct.pack('d', num_channels))
        
        # Write channel names
        for name in channel_names:
            write_string(f, name)
        
        # Write frequency info
        f.write(struct.pack('d', num_freqs))
        f.write(struct.pack('d', 1.0))  # isComplex
        
        # Write coordinates
        if is_uniform:
            # Write relative coordinates for uniform grid
            f.write(struct.pack(f'{len(x_unique)}d', *x_unique))
            f.write(struct.pack(f'{len(y_unique)}d', *y_unique))
            # Write absolute coordinates (same as relative)
            f.write(struct.pack(f'{len(x_unique)}d', *x_unique))
            f.write(struct.pack(f'{len(y_unique)}d', *y_unique))
        else:
            # Write relative coordinates for nonuniform
            f.write(struct.pack(f'{num_points}d', *x_data))
            f.write(struct.pack(f'{num_points}d', *y_data))
            # Write absolute coordinates (same as relative)
            f.write(struct.pack(f'{num_points}d', *x_data))
            f.write(struct.pack(f'{num_points}d', *y_data))
        
        # Write frequencies
        f.write(struct.pack(f'{num_freqs}d', *frequencies))
        
        print(f"Debug - Writing frequencies to .scan:")
        print(f"  First 3 freqs: {frequencies[:3]}")
        print(f"  Last 3 freqs: {frequencies[-3:]}")
        print(f"  Total written: {num_freqs}")
        
        # Prepare and write data
        # Format: for each point, all real values then all imaginary values
        if is_uniform:
            # Reshape to grid and handle raster scan pattern
            data_grid = data.reshape(len(y_unique), len(x_unique), num_freqs, num_channels)
            # Flip alternate rows for raster pattern
            data_grid[1::2, :, :, :] = data_grid[1::2, ::-1, :, :]
            # Flatten back
            data_flat = data_grid.reshape(-1, num_freqs, num_channels)
        else:
            data_flat = data
        
        # Interleave real and imaginary per point
        for point_idx in range(data_flat.shape[0]):
            for freq_idx in range(num_freqs):
                for chan_idx in range(num_channels):
                    val = data_flat[point_idx, freq_idx, chan_idx]
                    f.write(struct.pack('d', np.real(val)))
            for freq_idx in range(num_freqs):
                for chan_idx in range(num_channels):
                    val = data_flat[point_idx, freq_idx, chan_idx]
                    f.write(struct.pack('d', np.imag(val)))
    
    print(f"Successfully converted {hdf5_path} to {scan_path}")
    print(f"  Points: {num_points}")
    print(f"  Frequencies: {num_freqs}")
    print(f"  Frequency range (GHz): {frequencies[0]:.6f} to {frequencies[-1]:.6f}")
    print(f"  Channels: {num_channels}")
    print(f"  Uniform: {is_uniform}")
    
    return scan_path


def run_gui():
    """Run the GUI version of the converter"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Ask user to select input HDF5 file
    hdf5_path = filedialog.askopenfilename(
        title="Select HDF5 file to convert",
        filetypes=[("HDF5 files", "*.hdf5 *.h5"), ("All files", "*.*")]
    )
    
    if not hdf5_path:
        print("No file selected. Exiting.")
        return
    
    # Ask user where to save the .scan file
    default_scan = str(Path(hdf5_path).with_suffix('.scan'))
    scan_path = filedialog.asksaveasfilename(
        title="Save .scan file as",
        initialfile=Path(default_scan).name,
        defaultextension=".scan",
        filetypes=[("Scan files", "*.scan"), ("All files", "*.*")]
    )
    
    if not scan_path:
        print("No output file selected. Exiting.")
        return
    
    try:
        output_path = hdf5_to_scan(hdf5_path, scan_path)
        messagebox.showinfo("Success", f"Successfully converted to:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert HDF5 to .scan format')
    parser.add_argument('input', nargs='?', help='Input HDF5 file (optional if using GUI)')
    parser.add_argument('-o', '--output', help='Output .scan file (optional)')
    parser.add_argument('-d', '--description', default='', help='Scan description')
    parser.add_argument('--gui', action='store_true', help='Use GUI file picker')
    
    args = parser.parse_args()
    
    # If no input file provided or --gui flag used, run GUI
    if args.input is None or args.gui:
        run_gui()
    else:
        hdf5_to_scan(args.input, args.output, args.description)