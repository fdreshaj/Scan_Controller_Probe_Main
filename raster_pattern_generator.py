import numpy as np
import matplotlib.pyplot as plt
import csv

def create_pattern_matrix(n):
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

#step and len are in mm, step size should be quarter wavelength
step_size = 3.725

length = 60

n = int(length/step_size)

theta = np.deg2rad(-90)
# Also dont forget to multiply the final matrix by the step size to scale

mat = create_pattern_matrix(n)

rot_mat = rotate_points(mat,theta)

shear_mat = apply_shear(mat,0,1)

save_matrix_to_csv(rot_mat)

composite = apply_shear(rot_mat,1,0)
mat = step_size*mat

plt.figure(figsize=(10, 10))
#plt.plot(mat[0], mat[1], 'o-', markersize=8)
plt.plot(mat[0], mat[1], 'o-', markersize=8)
plt.title(f'2D Pattern Plot for n={n}')
plt.xlabel('Row 1 (X-axis)')
plt.ylabel('Row 2 (Y-axis)')
plt.grid(True)
plt.axis('equal')
plt.show()
