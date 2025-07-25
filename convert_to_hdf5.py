import h5py
import numpy as np



HDF5FILE = h5py.File(f"scantester.hdf5", mode="w")
arr = []

for i in range (0,6):
    arr.append(np.random.rand(1,10000))
    for j in range (0,6):
        HDF5FILE.create_group(f"/Coordinate({i},{j})")
        HDF5FILE.create_group(f"/Coordinate({i},{j})/S11")
        dset = HDF5FILE.create_dataset(f"/Coordinate({i},{j})/S11/data",data=arr)
        
print(dset[0])       
HDF5FILE.close()
#print(arr)
