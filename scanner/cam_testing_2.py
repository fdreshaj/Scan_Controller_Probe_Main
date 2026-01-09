# A simple GUI application to test multiple camera devices using OpenCV and Tkinter.
# Gemini generated code. Only for use as a quality of life improvement.
# Additional features I want to add in the future:
# a mode where the gui adds additional things to the camera feed like some kind of overlay for the scan bed.
# add additional information maybe, like the current date and time, humidity, temperature, etc.
# maybe some basic image processing, not sure what yet.

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import datetime
import os
import threading
import time

class CameraApp:
    def __init__(self, window, window_title="Camera App"):
        # Initialize the main window
        self.window = window
        self.window.title(window_title)
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Create a frame to hold the controls
        self.control_frame = tk.Frame(self.window)
        self.control_frame.pack(side=tk.BOTTOM, pady=10)

        # Create a label for the camera selection dropdown
        tk.Label(self.control_frame, text="Select Camera:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)

        # Find all available cameras
        self.available_cameras = self.find_cameras()
        if not self.available_cameras:
            messagebox.showerror("No Cameras Found", "No camera devices were detected.")
            self.on_closing()
            return
            
        # Create a dropdown menu to select the camera
        self.selected_camera = tk.StringVar(self.window)
        self.selected_camera.set(self.available_cameras[0])  # Set initial value
        self.camera_option_menu = tk.OptionMenu(self.control_frame, self.selected_camera, *self.available_cameras)
        self.camera_option_menu.pack(side=tk.LEFT, padx=5)

        # Trace the variable to call a function when the selection changes
        self.selected_camera.trace_add("write", self.change_camera)

        # Create buttons
        self.btn_toggle_text = tk.StringVar(value="Start Camera")
        self.btn_toggle = tk.Button(self.control_frame, textvariable=self.btn_toggle_text, command=self.toggle_camera, font=("Arial", 12))
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        self.btn_snapshot = tk.Button(self.control_frame, text="Take Snapshot", command=self.take_snapshot, font=("Arial", 12))
        self.btn_snapshot.pack(side=tk.LEFT, padx=5)
        self.btn_snapshot["state"] = "disabled" # Initially disabled

        self.btn_quit = tk.Button(self.control_frame, text="Quit", command=self.on_closing, font=("Arial", 12))
        self.btn_quit.pack(side=tk.LEFT, padx=5)

        # Create a label to display the camera feed
        self.video_source = int(self.selected_camera.get())
        self.vid = None
        self.canvas = tk.Label(self.window)
        self.canvas.pack()

        self.is_running = False
        self.delay = 15 # Delay in ms, equivalent to ~60 fps

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.window, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)
        self.progress_bar.pack_forget() # Hide it initially

    def find_cameras(self):
        """Detects all available camera devices."""
        index = 0
        arr = []
        while index < 10: # Check for up to 10 cameras
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) # Using CAP_DSHOW for faster detection on Windows
            if cap.read()[0]:
                arr.append(str(index))
            cap.release()
            index += 1
        return arr

    def change_camera(self, *args):
        """Disables controls, shows progress bar, and starts a thread to swap the video source."""
        # Disable all buttons and dropdown during the swap
        self.btn_toggle["state"] = "disabled"
        self.btn_snapshot["state"] = "disabled"
        self.camera_option_menu["state"] = "disabled"
        
        # Show the progress bar and force the UI to redraw
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()
        self.window.update_idletasks()

        # Start the camera change in a separate thread
        threading.Thread(target=self._run_camera_swap_in_thread, daemon=True).start()

    def _run_camera_swap_in_thread(self):
        """Handles the camera swap on a separate thread to prevent freezing."""
        
        self.stop_camera()
        
        # Update the video source to the new selection
        self.video_source = int(self.selected_camera.get())
        
        # Start the new camera
        self.start_camera()

        # Update the progress bar and re-enable controls on the main thread
        self.window.after(0, self.progress_bar.stop)
        self.window.after(0, self.progress_bar.pack_forget)
        self.window.after(0, lambda: self.btn_toggle.config(state="normal"))
        self.window.after(0, lambda: self.btn_snapshot.config(state="normal"))
        self.window.after(0, lambda: self.camera_option_menu.config(state="normal"))

    def toggle_camera(self):
        if self.is_running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        # Open the video source
        self.vid = cv2.VideoCapture(self.video_source)
        if not self.vid.isOpened():
            messagebox.showerror("Camera Error", f"Could not open camera device {self.video_source}.")
            return

        self.is_running = True
        self.btn_toggle_text.set("Stop Camera")
        self.btn_snapshot["state"] = "normal"
        self.update()

    def stop_camera(self):
        if self.vid and self.vid.isOpened():
            self.vid.release()
            self.canvas.config(image="") # Clear the canvas
        self.is_running = False
        self.btn_toggle_text.set("Start Camera")
        self.btn_snapshot["state"] = "disabled"

    def update(self):
        # Update the camera feed
        if self.is_running:
            ret, frame = self.vid.read()
            if ret:
                # Convert the image from BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.photo = ImageTk.PhotoImage(image=Image.fromarray(rgb_frame))
                self.canvas.config(image=self.photo)
            else:
                self.stop_camera() # Stop if there's an error reading the frame
                messagebox.showerror("Frame Error", "Could not read frame from camera.")
                return

            self.window.after(self.delay, self.update)
        # No 'else' needed here, as the loop stops naturally when is_running is False

    def take_snapshot(self):
        # Capture a single frame and save it
        if self.is_running:
            ret, frame = self.vid.read()
            if ret:
                # Create a snapshots directory if it doesn't exist
                if not os.path.exists("snapshots"):
                    os.makedirs("snapshots")

                # Generate a unique filename with a timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = os.path.join("snapshots", f"snapshot_{timestamp}.png")

                cv2.imwrite(filename, frame)
                print(f"Snapshot saved to {filename}")
            else:
                messagebox.showwarning("Snapshot Failed", "Could not capture a snapshot.")

    def get_current_frame(self):
        """Returns the current camera frame as a numpy array, or None if camera is not running."""
        if self.is_running and self.vid and self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                return frame
        return None

    def on_closing(self):
        # Stop the camera and destroy the window when closing
        self.stop_camera()
        self.window.destroy()

if __name__ == "__main__":
    # Create the main window
    root = tk.Tk()
    
    # Create the camera application instance
    app = CameraApp(root)
    
    # Run the Tkinter main loop
    root.mainloop()
