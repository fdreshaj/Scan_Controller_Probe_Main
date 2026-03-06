## Needed a quick csv to hdf5 tool, gemini one shotted  

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import numpy as np
import h5py
import os
from datetime import datetime

class CSVToHDF5Converter:
    """
    A Tkinter application to convert up to two CSV files (containing S-parameter data)
    into a single HDF5 file. Each CSV's data is stored in a separate group within
    the HDF5 file.
    """
    def __init__(self, master):
        self.master = master
        master.title("CSV to HDF5 Converter")
        master.geometry("600x400") # Set a default window size
        master.resizable(False, False) # Make window not resizable

        self.csv_path1 = tk.StringVar()
        self.csv_path2 = tk.StringVar()
        self.hdf5_filename = tk.StringVar(value="output_scan_data.h5")
        self.status_message = tk.StringVar()

        self._create_widgets()

    def _create_widgets(self):
        """Creates and arranges all GUI widgets."""
        # Styling
        style = ttk.Style()
        style.theme_use('clam') # Use a modern theme
        style.configure('TFrame', background='#e0e0e0')
        style.configure('TLabel', background='#e0e0e0', font=('Inter', 10))
        style.configure('TButton', font=('Inter', 10, 'bold'), padding=10)
        style.configure('TEntry', font=('Inter', 10), padding=5)

        main_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # CSV 1 Selection
        ttk.Label(main_frame, text="CSV File 1:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.csv_path1, width=50, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=lambda: self._select_csv_file(1)).grid(row=0, column=2, padx=5, pady=5)

        # CSV 2 Selection
        ttk.Label(main_frame, text="CSV File 2 (Optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.csv_path2, width=50, state='readonly').grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=lambda: self._select_csv_file(2)).grid(row=1, column=2, padx=5, pady=5)

        # HDF5 Output Filename
        ttk.Label(main_frame, text="Output HDF5 Filename:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.hdf5_filename, width=50).grid(row=2, column=1, padx=5, pady=5)

        # Convert Button
        ttk.Button(main_frame, text="Convert to HDF5", command=self._convert_to_hdf5).grid(row=3, column=0, columnspan=3, pady=20)

        # Status Message
        ttk.Label(main_frame, textvariable=self.status_message, wraplength=500, justify=tk.CENTER, foreground='blue').grid(row=4, column=0, columnspan=3, pady=10)

        # Configure column weights for responsiveness (though window is fixed size)
        main_frame.grid_columnconfigure(1, weight=1)

    def _select_csv_file(self, csv_num):
        """
        Opens a file dialog for selecting a CSV file and updates the corresponding StringVar.

        Args:
            csv_num (int): The number of the CSV file (1 or 2).
        """
        filepath = filedialog.askopenfilename(
            title=f"Select CSV File {csv_num}",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            if csv_num == 1:
                self.csv_path1.set(filepath)
            else:
                self.csv_path2.set(filepath)
            self.status_message.set(f"Selected CSV {csv_num}: {os.path.basename(filepath)}")

    def _parse_csv_data(self, filepath):
        """
        Parses the S-parameter data from a given CSV file.
        Assumes the CSV format:
        - First row is empty.
        - Second row is header (e.g., "Frequency (Hz)", "S11_Real", "S11_Imag").
        - Subsequent rows contain data.

        Args:
            filepath (str): The path to the CSV file.

        Returns:
            tuple: A tuple containing (frequencies_array, s_params_dict).
                   s_params_dict: { 'S11': np.array([complex_data]), ... }
            None: If an error occurs during parsing.
        """
        frequencies = []
        s_params_data = {} # Stores { 'S11': [complex_values], ... }

        try:
            with open(filepath, 'r', newline='') as f:
                reader = csv.reader(f)

                # Skip the first empty row
                try:
                    next(reader)
                except StopIteration:
                    messagebox.showerror("CSV Error", f"CSV file '{os.path.basename(filepath)}' is empty.")
                    return None

                # Read the header row
                header = next(reader)
                if not header:
                    messagebox.showerror("CSV Error", f"CSV file '{os.path.basename(filepath)}' has no header row.")
                    return None

                # Find frequency column index
                freq_col_idx = -1
                try:
                    freq_col_idx = header.index("Frequency (Hz)")
                except ValueError:
                    messagebox.showerror("CSV Error", f"CSV file '{os.path.basename(filepath)}' header missing 'Frequency (Hz)'.")
                    return None

                # Identify S-parameter columns
                s_param_cols = {} # { 'S11': {'real_idx': X, 'imag_idx': Y}, ... }
                for i, col_name in enumerate(header):
                    if col_name.endswith("_Real"):
                        s_param_name = col_name[:-5] # Remove '_Real'
                        if s_param_name not in s_param_cols:
                            s_param_cols[s_param_name] = {}
                        s_param_cols[s_param_name]['real_idx'] = i
                    elif col_name.endswith("_Imag"):
                        s_param_name = col_name[:-5] # Remove '_Imag'
                        if s_param_name not in s_param_cols:
                            s_param_cols[s_param_name] = {}
                        s_param_cols[s_param_name]['imag_idx'] = i

                # Validate S-parameter pairs (ensure real and imag exist)
                for s_name in list(s_param_cols.keys()):
                    if 'real_idx' not in s_param_cols[s_name] or 'imag_idx' not in s_param_cols[s_name]:
                        messagebox.showwarning("CSV Warning", f"S-parameter '{s_name}' in '{os.path.basename(filepath)}' is missing either Real or Imaginary part. Skipping this S-parameter.")
                        del s_param_cols[s_name]
                    else:
                        s_params_data[s_name] = [] # Initialize list for complex data

                if not s_param_cols:
                    messagebox.showerror("CSV Error", f"No valid S-parameter data found in '{os.path.basename(filepath)}'.")
                    return None

                # Read data rows
                for row_idx, row in enumerate(reader):
                    try:
                        # Ensure row has enough columns
                        if len(row) <= max(idx for s_info in s_param_cols.values() for idx in s_info.values()):
                            messagebox.showwarning("CSV Warning", f"Row {row_idx+3} in '{os.path.basename(filepath)}' is incomplete. Skipping.")
                            continue

                        freq = float(row[freq_col_idx])
                        frequencies.append(freq)

                        for s_name, indices in s_param_cols.items():
                            real_val = float(row[indices['real_idx']])
                            imag_val = float(row[indices['imag_idx']])
                            s_params_data[s_name].append(complex(real_val, imag_val))

                    except ValueError as ve:
                        messagebox.showwarning("CSV Warning", f"Data conversion error in row {row_idx+3} of '{os.path.basename(filepath)}': {ve}. Skipping row.")
                    except IndexError as ie:
                        messagebox.showwarning("CSV Warning", f"Column index error in row {row_idx+3} of '{os.path.basename(filepath)}': {ie}. Skipping row.")

            # Convert lists to numpy arrays
            frequencies = np.array(frequencies)
            for s_name in s_params_data:
                s_params_data[s_name] = np.array(s_params_data[s_name])

            return frequencies, s_params_data

        except FileNotFoundError:
            messagebox.showerror("File Error", f"CSV file not found: {filepath}")
            return None
        except Exception as e:
            messagebox.showerror("Processing Error", f"An unexpected error occurred while processing '{os.path.basename(filepath)}': {e}")
            return None

    def _convert_to_hdf5(self):
        """
        Initiates the conversion process from selected CSVs to an HDF5 file.
        """
        csv1_path = self.csv_path1.get()
        csv2_path = self.csv_path2.get()
        output_hdf5_name = self.hdf5_filename.get()

        if not csv1_path:
            messagebox.showwarning("Input Error", "Please select at least one CSV file.")
            return

        if not output_hdf5_name:
            messagebox.showwarning("Input Error", "Please provide an output HDF5 filename.")
            return

        # Prepare data containers
        all_scans_data = [] # List to hold (frequencies, s_params_dict, original_filename) for each CSV

        # Process CSV 1
        self.status_message.set(f"Processing '{os.path.basename(csv1_path)}'...")
        self.master.update_idletasks() # Update GUI
        data1 = self._parse_csv_data(csv1_path)
        if data1:
            all_scans_data.append((data1[0], data1[1], os.path.basename(csv1_path)))
        else:
            self.status_message.set("Failed to process CSV 1.")
            return

        # Process CSV 2 if selected
        if csv2_path:
            self.status_message.set(f"Processing '{os.path.basename(csv2_path)}'...")
            self.master.update_idletasks() # Update GUI
            data2 = self._parse_csv_data(csv2_path)
            if data2:
                all_scans_data.append((data2[0], data2[1], os.path.basename(csv2_path)))
            else:
                self.status_message.set("Failed to process CSV 2.")
                return

        if not all_scans_data:
            self.status_message.set("No valid data processed from CSVs.")
            return

        # Save to HDF5
        try:
            with h5py.File(output_hdf5_name, 'a') as f: # 'a' mode for append (create if not exists)
                for i, (freqs, s_params, original_filename) in enumerate(all_scans_data):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    # Create a unique group name for each CSV's data
                    group_name = f"csv_scan_{i+1}_{timestamp}"

                    # Ensure group name is unique if a file already exists with that name
                    # (though timestamp should handle this for new runs)
                    counter = 0
                    base_group_name = group_name
                    while group_name in f:
                        counter += 1
                        group_name = f"{base_group_name}_{counter}"

                    scan_group = f.create_group(group_name)

                    # Save frequencies
                    scan_group.create_dataset("frequencies", data=freqs)

                    # Save S-parameters (real and imag parts)
                    for s_name, complex_array in s_params.items():
                        scan_group.create_dataset(f"{s_name}_real", data=complex_array.real)
                        scan_group.create_dataset(f"{s_name}_imag", data=complex_array.imag)

                    # Add metadata as attributes
                    scan_group.attrs['original_csv_filename'] = original_filename
                    scan_group.attrs['processed_at'] = datetime.now().isoformat()
                    self.status_message.set(f"Saved data from '{original_filename}' to HDF5 group: '{group_name}'")
                    self.master.update_idletasks() # Update GUI

            self.status_message.set(f"Successfully converted CSV(s) to HDF5 file: {output_hdf5_name}")
            messagebox.showinfo("Success", f"Data successfully saved to {output_hdf5_name}")

        except Exception as e:
            self.status_message.set(f"Error saving to HDF5: {e}")
            messagebox.showerror("HDF5 Save Error", f"An error occurred while saving to HDF5: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CSVToHDF5Converter(root)
    root.mainloop()