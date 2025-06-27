import numpy as np
import matplotlib.pyplot as plt
import csv

def create_pattern_matrix(n):
    #generates (n+1)^2 (x,y) column
    row1 = np.repeat(np.arange(n+1), n+1)
    row2 = []
    for i in range(n+1):
        if i % 2 == 0:
            row2.extend(range(n+1))        
        else:
            row2.extend(range(n, -1, -1))   
    return np.array([row1, row2])



def rotate_points(matrix, theta_rad):
    
    R = np.array([
        [np.cos(theta_rad), -np.sin(theta_rad)],
        [np.sin(theta_rad),  np.cos(theta_rad)]
    ])
    
    R = R @ matrix
    R[np.abs(R) < 1e-10] = 0
    
    
    return R 

    
def apply_shear(matrix, shear_x=0.0, shear_y=0.0):
    shear_matrix = np.array([
        [1, shear_x],
        [shear_y, 1]
    ])
    
    shear_matrix = shear_matrix @ matrix
    
    shear_matrix[np.abs(shear_matrix) < 1e-10] = 0

    return shear_matrix



def save_matrix_to_csv(matrix, filename='matrix_output.csv'):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        for row in matrix:
            writer.writerow(row)

def plot(mat,n):
    plt.figure(figsize=(10, 10))
    #plt.plot(mat[0], mat[1], 'o-', markersize=8)
    plt.plot(mat[0], mat[1], 'o-', markersize=8)
    plt.title(f'2D Pattern Plot for n={n}')
    plt.xlabel('Row 1 (X-axis)')
    plt.ylabel('Row 2 (Y-axis)')
    plt.grid(True)
    plt.axis('equal')
    plt.show()
    
def hilbert_curve(n):
    # https://blogs.mathworks.com/steve/2012/01/25/generating-hilbert-curves/
    # the number of points is related by 4^order, setting max order to 8 for now due to rapid growth 
    # if you want to manipulate the curve you need to change z, you can translate, rotate, scale etc.
    #will not be the same as the normal matrix for non order of 2 powers, working on fixing that
    order = int(np.log2(n))
    if order <= 8: 
        a = 1 + 1j
        b = 1 - 1j
        z = np.array([0], dtype=complex)

        for _ in range(order):
            w = 1j * np.conj(z)
            z = np.concatenate([
                w - a,
                z - b,
                z + a,
                b - w
            ]) / 2
    elif order>8:
        print("Order limited to 8 ~ 348.949 GHz") 
    elif order<0:
        print("4^k points, k<0 does not make sense to have fractional number of points")

    return np.vstack((z.real, z.imag))
