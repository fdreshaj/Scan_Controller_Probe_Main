import os
os.environ["QT_API"] = "pyside6"
import sys
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QApplication, QDoubleSpinBox, QMessageBox
)

class ndwindow(QWidget):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("SAR Raster 4D Transformer")
        self.resize(1200, 850)
        self.mesh = None 
        self.points_matrix = np.array([]) # Base XYZ
        self.points_4d = np.array([])     # Transformed XYZ + Angle
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.control_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📁 Load STL")
        self.import_btn.clicked.connect(self.import_new_file)
        
        self.step_input = QDoubleSpinBox()
        self.step_input.setRange(0.01, 100.0)
        self.step_input.setValue(1.0) 
        self.step_input.setSuffix(" mm")

        self.standoff_input = QDoubleSpinBox()
        self.standoff_input.setRange(0.0, 500.0)
        self.standoff_input.setValue(5.0) 
        self.standoff_input.setSuffix(" mm")

        self.project_btn = QPushButton("1. Generate Raster")
        self.project_btn.clicked.connect(self.run_surface_projection)

        self.transform_btn = QPushButton("2. Apply Normal Transformation")
        self.transform_btn.clicked.connect(self.apply_voxel_4d_transformation)

        self.control_layout.addWidget(self.import_btn)
        self.control_layout.addWidget(QLabel("Step:"))
        self.control_layout.addWidget(self.step_input)
        self.control_layout.addWidget(QLabel("Standoff:"))
        self.control_layout.addWidget(self.standoff_input)
        self.control_layout.addWidget(self.project_btn)
        self.control_layout.addWidget(self.transform_btn)
        self.control_layout.addStretch()
        
        self.plotter = QtInteractor(self)
        self.plotter.set_background("#121212")
        self.plotter.add_axes()
        
        self.main_layout.addLayout(self.control_layout)
        self.main_layout.addWidget(self.plotter.interactor)

    def get_z_at_xy(self, x, y, bounds):
        x = np.clip(x, bounds[0], bounds[1])
        start = [x, y, bounds[5] + 10]
        stop = [x, y, bounds[4] - 10]
        points, _ = self.mesh.ray_trace(start, stop)
        return points[0] if len(points) > 0 else None

    def run_surface_projection(self):
        """Standard Raster Generation (Stage 1)"""
        if self.mesh is None: return
        b = self.mesh.bounds
        target_dist = self.step_input.value()
        raw_list = [] 

        y_range = np.linspace(b[2], b[3], int(np.ceil((b[3] - b[2]) / target_dist)) + 1)
        for row_idx, y in enumerate(y_range):
            row_points = []
            x = b[0]
            p_prev = self.get_z_at_xy(x, y, b)
            if p_prev is not None: row_points.append(p_prev)

            while x < b[1]:
                dx = target_dist 
                for _ in range(5): 
                    p_next = self.get_z_at_xy(x + dx, y, b)
                    if p_next is None: break
                    actual_dist = np.linalg.norm(p_next - p_prev)
                    if actual_dist < 1e-6: break 
                    dx = dx * (target_dist / actual_dist)
                x += dx
                if x >= b[1]:
                    p_final = self.get_z_at_xy(b[1], y, b)
                    if p_final is not None: row_points.append(p_final)
                    break
                p_prev = self.get_z_at_xy(x, y, b)
                if p_prev is not None: row_points.append(p_prev)
                else: x += target_dist

            if row_idx % 2 != 0: row_points.reverse()
            raw_list.extend(row_points)

        self.points_matrix = np.array(raw_list)
        self.visualize_path(self.points_matrix)
        print(f"Base Raster Generated: {len(self.points_matrix)} points.")

    def generate_offset_mesh(self, original_mesh, standoff):
        """
        Creates a new mesh surface shifted outward by the standoff distance.
        This replaces the simple scaling 'enlargement' with a true offset.
        """
        # 1. Compute surface normals if they don't exist
        mesh = original_mesh.compute_normals(cell_normals=False, point_normals=True, inplace=False)
        
        # 2. Offset the points along their normals
        # This is the "Enlargement" you described, but done correctly point-by-point
        offset_points = mesh.points + (mesh.point_data['Normals'] * standoff)
        
        # 3. Create the new mesh
        offset_mesh = mesh.copy()
        offset_mesh.points = offset_points
        return offset_mesh


    def apply_voxel_4d_transformation(self):
        """Voxel-based transformation using Signed Distance Fields (SDF)"""
        if self.mesh is None:
            QMessageBox.warning(self, "Error", "Load an STL first!")
            return

        standoff = self.standoff_input.value()
        step = self.step_input.value()
        
        # 1. Create a Voxel Grid around the mesh
        # We expand the bounds slightly to ensure the standoff fits inside
        b = np.array(self.mesh.bounds)
        padding = standoff + (step * 2)
        grid_bounds = [b[0]-padding, b[1]+padding, b[2]-padding, b[3]+padding, b[4]-padding, b[5]+padding]
        
        # Create uniform grid (Voxels)
        dims = (
            int((grid_bounds[1] - grid_bounds[0]) / step),
            int((grid_bounds[3] - grid_bounds[2]) / step),
            int((grid_bounds[5] - grid_bounds[4]) / step)
        )
        grid = pv.ImageData(dimensions=dims, spacing=(step, step, step), origin=(grid_bounds[0], grid_bounds[2], grid_bounds[4]))
        
        # 2. Compute the Signed Distance Field (SDF)
        # This gives every point in the grid a distance to the mesh surface
        grid = grid.compute_implicit_distance(self.mesh, inplace=True)
        
        # 3. Extract the Isosurface at 'standoff' distance
        # This creates a perfectly smooth offset shell without mesh errors
        offset_shell = grid.contour(isosurfaces=[standoff], scalars="implicit_distance")
        
        if offset_shell.n_points == 0:
            QMessageBox.critical(self, "Error", "Standoff is too large for the voxel grid.")
            return

        # 4. Rasterize the Shell
        # Now we just need to pull the Z-heights from this perfectly offset shell
        raw_4d = []
        shell_bounds = offset_shell.bounds
        z_up = np.array([0, 0, 1])
        
        y_range = np.arange(shell_bounds[2], shell_bounds[3], step)
        x_range = np.arange(shell_bounds[0], shell_bounds[1], step)

        for i, y in enumerate(y_range):
            current_x_list = x_range[::-1] if i % 2 != 0 else x_range
            for x in current_x_list:
                # Find the highest point on the shell at this XY
                # Since the shell is the offset, we don't need to project anymore
                point = self.get_top_point_from_mesh(offset_shell, x, y)
                if point is not None:
                    # Get normal from ORIGINAL mesh to find angle
                    cell_id = self.mesh.find_closest_cell(point)
                    normal = self.mesh.cell_normals[cell_id]
                    angle = np.degrees(np.arccos(np.clip(np.dot(normal, z_up), -1.0, 1.0)))
                    
                    raw_4d.append([point[0], point[1], point[2], angle])

        self.points_4d = np.array(raw_4d)
        self.visualize_path(self.points_4d[:, :3])
        print(f"Voxel transformation complete: {len(self.points_4d)} points.")

    def get_top_point_from_mesh(self, mesh, x, y):
        """Helper to find the highest Z on a mesh for a given XY"""
        # Using a small vertical line to find intersection with our offset shell
        start = [x, y, mesh.bounds[5] + 5]
        stop = [x, y, mesh.bounds[4] - 5]
        points, _ = mesh.ray_trace(start, stop)
        return points[0] if len(points) > 0 else None

    def visualize_path(self, pts):
        self.plotter.remove_actor("raster_path")
        self.plotter.remove_actor("raster_points")
        self.plotter.add_mesh(pv.lines_from_points(pts), color="#00e5ff", line_width=2, name="raster_path")
        self.plotter.add_mesh(pts, color="#ff00ff", point_size=4, name="raster_points")

    def import_new_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Mesh", "", "3D Files (*.stl *.obj)")
        if file:
            self.mesh = pv.read(file)
            self.mesh.compute_normals(inplace=True, cell_normals=True)
            self.plotter.clear()
            self.plotter.add_mesh(self.mesh, color="silver", opacity=0.3)
            self.plotter.reset_camera()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ndwindow()
    window.show()
    sys.exit(app.exec())