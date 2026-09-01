
1. start up the shockline application before starting the python app. 2. Run test_scanner_gui.py. 3. Connect motion controller. 4. Connect probe controller. 5. Generate the scan pattern. 6. Finish file config. 7. Start Scan.

Progress is currently seen in the command line

Python 3.12.7 

pip install alive-progress==3.3.0 h5py==3.15.1 matplotlib==3.10.8 numpy==2.2.6 opencv-python==4.12.0.88 pyserial==3.5 PySide6==6.10.1 pytz==2025.2 PyVISA==1.16.0 pyzmq==27.1.0 scikit-rf==1.9.0 scipy==1.16.3 zmq==0.0.0 pyqtdarktheme pyvistaqt pyvista

For Gcode motion drivers use plugin named "bigtreetechMotor"
For Gecko motion drivers use plugin named "motion_controller_plugin"

For VNA connection use plugin named "Simplified_VNA_Plugin"

## Viewing a scan on its own

The S-parameter visualizer runs without the scanner GUI, for looking at scans
after the fact:

    python -m scanner.S_param_visualizer              # opens empty; use Import
    python -m scanner.S_param_visualizer scan.h5      # opens that file

With no argument the window opens with everything greyed out except the
Import button. The same window is reachable from inside the scanner GUI, where
it follows the running scan live.

### Playback and display

**Speed** sets how fast Play steps through the axis, 1-60 fps (default 8). The
readout beside it shows how long one full pass takes, and warns if the render
cannot keep up with the rate you asked for.

**Upscale** sets how many pixels each measurement point is drawn as (1x-16x).
A scan grid is coarse -- a 24 x 18 raster is 24 x 18 pixels -- so it needs
enlarging to be legible. **Smoothing** chooses how the gaps are filled:

* `Nearest` - one flat block per point. Every pixel is a measured value.
* `Bilinear` - blends between neighbouring points. Much easier to read on a
  coarse grid, but the gradient between two points is interpolation, not data.

Both are display settings only. The stored data is untouched, and clicking the
heatmap still selects the real measurement point underneath.
