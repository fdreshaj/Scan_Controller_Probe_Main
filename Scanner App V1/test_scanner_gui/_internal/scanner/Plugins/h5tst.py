import h5py
import numpy as np
from tkinter import filedialog
import tkinter as tk

root = tk.Tk()
root.withdraw()
filepath = filedialog.askopenfilename(title="Select HDF5 File", filetypes=[("HDF5 Files", "*.hdf5 *.h5")])

with h5py.File(filepath, "r") as f:
    data_real = f['/Data/S11_real'][:, 0]
    
    print("First 10 data values:")
    for i in range(10):
        print(f"  data[{i}] = {data_real[i]:.6f}")
    
    print(f"\ndata[0] == data[1]? {np.isclose(data_real[0], data_real[1])}")
    print(f"data[1] == data[2]? {np.isclose(data_real[1], data_real[2])}")