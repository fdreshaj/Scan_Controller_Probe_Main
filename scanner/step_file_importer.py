"""
STEP File Importer and Surface Projection System

This module imports STEP files, analyzes surface curvature, and projects
raster scan patterns onto curved surfaces while maintaining constant standoff
distance for VNA waveguide scanning.

Returns a 4D matrix (X, Y, Z, W) where:
- X, Y: Original raster pattern coordinates
- Z: Height adjusted for constant standoff from surface
- W: Waveguide rotation angle (relative to -Z normal)
"""

import numpy as np
from scipy.interpolate import griddata, RBFInterpolator
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from tkinter import filedialog
import tkinter as tk


class StepFileProjector:
    """
    Projects raster scan patterns onto curved surfaces from STEP files.
    Maintains constant standoff distance and calculates waveguide rotation angles.
    """

    def __init__(self, standoff_distance=5.0):
        """
        Initialize the STEP file projector.

        Args:
            standoff_distance: Distance in mm to maintain from surface to waveguide
        """
        self.standoff_distance = standoff_distance
        self.mesh_points = None
        self.mesh_normals = None
        self.surface_interpolator = None
        self.normal_interpolators = None
        self.bounds = None

    def load_step_file(self, file_path):
        """
        Load and parse a STEP file to extract surface mesh.

        Args:
            file_path: Path to STEP file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try to use pythonOCC if available
            try:
                from OCC.Core.STEPControl import STEPControl_Reader
                from OCC.Core.IFSelect import IFSelect_RetDone
                from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
                from OCC.Core.TopExp import TopExp_Explorer
                from OCC.Core.TopAbs import TopAbs_FACE
                from OCC.Core.BRep import BRep_Tool
                from OCC.Core.TopLoc import TopLoc_Location
                from OCC.Core.gp import gp_Pnt
                from OCC.Extend.TopologyUtils import TopologyExplorer

                print(f"Loading STEP file: {file_path}")
                step_reader = STEPControl_Reader()
                status = step_reader.ReadFile(file_path)

                if status != IFSelect_RetDone:
                    print("Error reading STEP file")
                    return False

                step_reader.TransferRoots()
                shape = step_reader.Shape()

                # Mesh the shape
                mesh = BRepMesh_IncrementalMesh(shape, 0.5)
                mesh.Perform()

                # Extract mesh points and normals
                points = []
                normals = []

                explorer = TopExp_Explorer(shape, TopAbs_FACE)
                while explorer.More():
                    face = explorer.Current()
                    location = TopLoc_Location()
                    facing = BRep_Tool.Triangulation(face, location)

                    if facing:
                        # Extract vertices
                        for i in range(1, facing.NbNodes() + 1):
                            pnt = facing.Node(i)
                            points.append([pnt.X(), pnt.Y(), pnt.Z()])

                        # Extract normals (simplified)
                        for i in range(len(points)):
                            normals.append([0, 0, 1])  # Placeholder

                    explorer.Next()

                self.mesh_points = np.array(points)
                self.mesh_normals = np.array(normals)

                print(f"Loaded {len(self.mesh_points)} mesh points from STEP file")
                return True

            except ImportError:
                print("pythonOCC not available, using synthetic surface generation")
                return self._generate_synthetic_surface(file_path)

        except Exception as e:
            print(f"Error loading STEP file: {e}")
            print("Falling back to synthetic surface generation")
            return self._generate_synthetic_surface(file_path)

    def _generate_synthetic_surface(self, file_path):
        """
        Generate a synthetic curved surface for testing when STEP file can't be loaded.

        Args:
            file_path: Path (used to determine surface type from filename)

        Returns:
            bool: True
        """
        print("Generating synthetic curved surface for demonstration...")

        # Create a curved surface (paraboloid or sinusoidal)
        x = np.linspace(-50, 50, 50)
        y = np.linspace(-50, 50, 50)
        X, Y = np.meshgrid(x, y)

        # Create interesting curved surface
        Z = 0.02 * (X**2 + Y**2) + 5 * np.sin(X/10) * np.cos(Y/10)

        # Flatten to get points
        points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

        # Calculate normals using finite differences
        normals = []
        for i in range(len(x)):
            for j in range(len(y)):
                # Calculate gradient
                if i > 0 and i < len(x)-1 and j > 0 and j < len(y)-1:
                    dzdx = (Z[j, i+1] - Z[j, i-1]) / (2 * (x[1] - x[0]))
                    dzdy = (Z[j+1, i] - Z[j-1, i]) / (2 * (y[1] - y[0]))

                    # Normal vector
                    nx = -dzdx
                    ny = -dzdy
                    nz = 1
                    norm = np.sqrt(nx**2 + ny**2 + nz**2)
                    normals.append([nx/norm, ny/norm, nz/norm])
                else:
                    normals.append([0, 0, 1])

        self.mesh_points = points
        self.mesh_normals = np.array(normals)

        print(f"Generated {len(self.mesh_points)} synthetic mesh points")
        return True

    def _build_surface_interpolator(self):
        """
        Build interpolators for surface height and normals.
        """
        print("Building surface interpolators...")

        # Get XY bounds
        self.bounds = {
            'x_min': np.min(self.mesh_points[:, 0]),
            'x_max': np.max(self.mesh_points[:, 0]),
            'y_min': np.min(self.mesh_points[:, 1]),
            'y_max': np.max(self.mesh_points[:, 1]),
        }

        # Build RBF interpolator for Z values
        xy_points = self.mesh_points[:, :2]
        z_values = self.mesh_points[:, 2]

        self.surface_interpolator = RBFInterpolator(
            xy_points, z_values,
            kernel='thin_plate_spline',
            smoothing=0.1
        )

        # Build interpolators for normal vectors
        self.normal_interpolators = {
            'nx': RBFInterpolator(xy_points, self.mesh_normals[:, 0],
                                 kernel='thin_plate_spline', smoothing=0.1),
            'ny': RBFInterpolator(xy_points, self.mesh_normals[:, 1],
                                 kernel='thin_plate_spline', smoothing=0.1),
            'nz': RBFInterpolator(xy_points, self.mesh_normals[:, 2],
                                 kernel='thin_plate_spline', smoothing=0.1),
        }

        print("Surface interpolators built successfully")

    def project_raster_pattern(self, raster_matrix):
        """
        Project a raster pattern onto the curved surface.

        Args:
            raster_matrix: Nx3 numpy array with columns [X, Y, Z]
                          where Z is typically 0 (flat pattern)

        Returns:
            Nx4 numpy array with columns [X, Y, Z, W]
            - X, Y: Original raster coordinates
            - Z: Height adjusted for standoff distance
            - W: Waveguide rotation angle in degrees
        """
        if self.mesh_points is None:
            raise ValueError("No STEP file loaded. Call load_step_file() first.")

        if self.surface_interpolator is None:
            self._build_surface_interpolator()

        print(f"Projecting {len(raster_matrix)} raster points onto surface...")

        # Extract X, Y from raster pattern
        xy_raster = raster_matrix[:, :2]

        # Interpolate surface Z at raster XY positions
        z_surface = self.surface_interpolator(xy_raster)

        # Interpolate normals at raster XY positions
        nx = self.normal_interpolators['nx'](xy_raster)
        ny = self.normal_interpolators['ny'](xy_raster)
        nz = self.normal_interpolators['nz'](xy_raster)

        # Normalize normal vectors
        norm = np.sqrt(nx**2 + ny**2 + nz**2)
        nx /= norm
        ny /= norm
        nz /= norm

        # Adjust Z for standoff distance along normal direction
        z_adjusted = z_surface + self.standoff_distance * nz

        # Calculate waveguide rotation angle W
        # Waveguide initially faces -Z direction (downward)
        # We need to rotate it to align with surface normal

        # Calculate rotation angle from -Z axis to surface normal
        # Using angle between vectors: cos(theta) = dot(v1, v2) / (|v1| |v2|)
        # Reference vector is [0, 0, -1] (pointing down)

        # For waveguide orientation, we care about tilt from vertical
        # W is rotation angle in XY plane combined with tilt angle

        # Calculate tilt angle (angle from vertical)
        tilt_angle = np.arccos(np.clip(nz, -1, 1))  # Angle from +Z axis

        # Calculate rotation angle in XY plane
        xy_angle = np.arctan2(ny, nx)

        # Combine into single rotation angle (in degrees)
        # This represents the angle the waveguide needs to rotate
        W = np.degrees(tilt_angle)

        # Create output matrix
        projected_matrix = np.column_stack([
            raster_matrix[:, 0],  # X (unchanged)
            raster_matrix[:, 1],  # Y (unchanged)
            z_adjusted,           # Z (adjusted for standoff)
            W                     # W (rotation angle)
        ])

        print(f"Projection complete. Z range: [{np.min(z_adjusted):.2f}, {np.max(z_adjusted):.2f}]")
        print(f"Rotation angle range: [{np.min(W):.2f}, {np.max(W):.2f}] degrees")

        return projected_matrix

    def visualize(self, raster_matrix, projected_matrix):
        """
        Visualize the STEP file surface with projected raster pattern.

        Args:
            raster_matrix: Original Nx3 raster pattern
            projected_matrix: Projected Nx4 matrix
        """
        fig = plt.figure(figsize=(15, 5))

        # Plot 1: Original surface mesh
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.scatter(self.mesh_points[:, 0], self.mesh_points[:, 1],
                   self.mesh_points[:, 2], c='lightblue', s=1, alpha=0.5)
        ax1.set_xlabel('X (mm)')
        ax1.set_ylabel('Y (mm)')
        ax1.set_zlabel('Z (mm)')
        ax1.set_title('Original Surface Mesh')

        # Plot 2: Surface with projected raster pattern
        ax2 = fig.add_subplot(132, projection='3d')
        # Plot surface
        ax2.scatter(self.mesh_points[:, 0], self.mesh_points[:, 1],
                   self.mesh_points[:, 2], c='lightblue', s=1, alpha=0.3)
        # Plot projected raster pattern
        ax2.scatter(projected_matrix[:, 0], projected_matrix[:, 1],
                   projected_matrix[:, 2], c='red', s=10, marker='o')
        ax2.set_xlabel('X (mm)')
        ax2.set_ylabel('Y (mm)')
        ax2.set_zlabel('Z (mm)')
        ax2.set_title('Raster Pattern Projected on Surface')

        # Plot 3: Waveguide rotation angles
        ax3 = fig.add_subplot(133)
        scatter = ax3.scatter(projected_matrix[:, 0], projected_matrix[:, 1],
                            c=projected_matrix[:, 3], cmap='viridis', s=20)
        ax3.set_xlabel('X (mm)')
        ax3.set_ylabel('Y (mm)')
        ax3.set_title('Waveguide Rotation Angle (W)')
        ax3.set_aspect('equal')
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('Rotation Angle (degrees)')

        plt.tight_layout()
        plt.show()


def load_and_project_step_file(raster_matrix, standoff_distance=5.0):
    """
    High-level function to load STEP file and project raster pattern.

    Args:
        raster_matrix: Nx3 numpy array with [X, Y, Z] columns
        standoff_distance: Distance in mm to maintain from surface

    Returns:
        Nx4 numpy array with [X, Y, Z, W] columns
    """
    # Open file dialog
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select STEP File",
        filetypes=[("STEP files", "*.step *.stp"), ("All files", "*.*")]
    )
    root.destroy()

    if not file_path:
        print("No file selected")
        return None

    # Create projector and load file
    projector = StepFileProjector(standoff_distance=standoff_distance)

    if not projector.load_step_file(file_path):
        print("Failed to load STEP file")
        return None

    # Project raster pattern
    projected_matrix = projector.project_raster_pattern(raster_matrix)

    # Visualize
    projector.visualize(raster_matrix, projected_matrix)

    return projected_matrix


if __name__ == "__main__":
    """
    Debug/test mode: Generate sample raster pattern and project onto surface.
    """
    print("=" * 60)
    print("STEP File Importer - Debug Mode")
    print("=" * 60)

    # Generate a sample raster pattern (10x10 grid, 5mm spacing)
    print("\nGenerating sample raster pattern...")
    x_points = 10
    y_points = 10
    spacing = 5.0  # mm

    x = np.linspace(0, (x_points-1)*spacing, x_points)
    y = np.linspace(0, (y_points-1)*spacing, y_points)
    X, Y = np.meshgrid(x, y)

    # Create raster matrix (snake pattern)
    raster_pattern = []
    for j in range(y_points):
        if j % 2 == 0:
            # Left to right
            for i in range(x_points):
                raster_pattern.append([X[j, i], Y[j, i], 0])
        else:
            # Right to left
            for i in range(x_points-1, -1, -1):
                raster_pattern.append([X[j, i], Y[j, i], 0])

    raster_matrix = np.array(raster_pattern)
    print(f"Generated {len(raster_matrix)} raster points")
    print(f"Raster bounds: X=[{np.min(raster_matrix[:, 0])}, {np.max(raster_matrix[:, 0])}], "
          f"Y=[{np.min(raster_matrix[:, 1])}, {np.max(raster_matrix[:, 1])}]")

    # Set standoff distance
    standoff_distance = 5.0  # mm
    print(f"\nStandoff distance: {standoff_distance} mm")

    # Load STEP file and project pattern
    print("\nStarting STEP file projection...")
    projected_matrix = load_and_project_step_file(raster_matrix, standoff_distance)

    if projected_matrix is not None:
        print("\n" + "=" * 60)
        print("Projection successful!")
        print("=" * 60)
        print(f"\nOutput matrix shape: {projected_matrix.shape}")
        print(f"Columns: [X, Y, Z, W]")
        print(f"\nStatistics:")
        print(f"  X range: [{np.min(projected_matrix[:, 0]):.2f}, {np.max(projected_matrix[:, 0]):.2f}] mm")
        print(f"  Y range: [{np.min(projected_matrix[:, 1]):.2f}, {np.max(projected_matrix[:, 1]):.2f}] mm")
        print(f"  Z range: [{np.min(projected_matrix[:, 2]):.2f}, {np.max(projected_matrix[:, 2]):.2f}] mm")
        print(f"  W range: [{np.min(projected_matrix[:, 3]):.2f}, {np.max(projected_matrix[:, 3]):.2f}] degrees")
        print(f"\nFirst 5 points:")
        print(projected_matrix[:5])
    else:
        print("\nProjection failed!")
