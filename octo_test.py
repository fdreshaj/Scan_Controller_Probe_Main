import pyvisa

# This class structure mimics the plugin architecture seen in Simplified_VNA_Plugin.py
# For a standalone script, you might not need to inherit from a base class like ProbePlugin,
# but this demonstrates how you would integrate PyVISA into such a system.
class GCode_Plugin:
    """
    A plugin-like class for connecting to a VISA device and sending G-code commands.
    """

    def __init__(self):
        """
        Initializes the GCode_Plugin.
        It sets up the ResourceManager and attempts to find a VISA device.
        """
        self.rm = None          # PyVISA ResourceManager instance
        self.driver = None      # PyVISA instrument driver instance
        self.resource_name = None # Stores the VISA resource name of the connected device
        self.timeout = 10000    # Default timeout in milliseconds

        # Initialize ResourceManager
        try:
            self.rm = pyvisa.ResourceManager()
            print("PyVISA ResourceManager initialized.")
        except Exception as e:
            print(f"Error initializing PyVISA ResourceManager: {e}")
            print("Please ensure that a VISA backend (e.g., NI-VISA, Keysight VISA) is installed and configured correctly.")
            return

        # Attempt to find a VISA device and set the resource_name
        self._find_and_set_device_resource()

    def _find_and_set_device_resource(self):
        """
        Internal method to find connected VISA devices and set the resource_name.
        """
        if not self.rm:
            print("ResourceManager not initialized. Cannot find devices.")
            return

        try:
            devices = self.rm.list_resources()

            if devices:
                print("Found the following VISA devices:")
                for device in devices:
                    print(f"- {device}")
                self.resource_name = devices[0] # Use the first found device
                print(f"Selected device: {self.resource_name}")
            else:
                print("No VISA devices found.")
                self.resource_name = None

        except pyvisa.errors.VisaIOError as e:
            print(f"VISA Error during device discovery: {e}")
            print("Ensure your VISA backend is correctly installed and configured.")
        except Exception as e:
            print(f"An unexpected error occurred during device discovery: {e}")

    def connect(self):
        """
        Connects to the VISA device identified during initialization.
        Sets the timeout and prints connection status.
        """
        if not self.resource_name:
            print("No VISA device selected or found. Cannot connect.")
            return

        if not self.rm:
            print("ResourceManager not initialized. Cannot connect.")
            return

        try:
            # Open the resource using the ResourceManager
            self.driver = self.rm.open_resource(self.resource_name)
            print(f"\nSuccessfully connected to: {self.resource_name}")

            # Set the timeout for read and write operations
            self.driver.timeout = self.timeout
            print(f"Communication timeout set to {self.timeout} ms.")

            # For serial instruments (ASRL), it's often good practice to explicitly set
            # the read_termination character if the device uses one (e.g., newline).
            # This helps the driver know when a response is complete.
            # If your G-code device terminates lines with '\n', uncomment the line below:
            # self.driver.read_termination = '\n'
            # Also, set the write_termination if the device expects it (e.g., '\n'):
            # self.driver.write_termination = '\n'


        except pyvisa.errors.VisaIOError as e:
            print(f"VISA I/O Error connecting to {self.resource_name}: {e}")
            self.driver = None # Ensure driver is None if connection fails
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            self.driver = None

    def disconnect(self):
        """
        Closes the connection to the VISA device.
        """
        if self.driver:
            try:
                self.driver.close()
                print(f"Connection to {self.resource_name} closed.")
            except Exception as e:
                print(f"Error closing connection to {self.resource_name}: {e}")
            finally:
                self.driver = None # Clear the driver reference
        else:
            print("No active connection to disconnect.")

    def send_gcode_command(self, command):
        """
        Sends a G-code command to the connected device and reads the response.
        Uses the query() method which combines write and read operations.

        Args:
            command (str): The G-code command to send (e.g., "M114").
                           A newline character will be appended automatically if not present.

        Returns:
            str: The response from the device, or None if an error occurs.
        """
        if not self.driver:
            print("Not connected to a device. Please call connect() first.")
            return None

        # Ensure the command ends with a newline, as is common for G-code devices
        # The query method will handle sending the command and reading the response
        # based on the instrument's read_termination setting.
        if not command.endswith('\n'):
            command += '\n'

        q_response = None
        try:
            print(f"Sending G-code command: '{command.strip()}'")
            # Use query() which is a convenience method for write() followed by read()
            q_response = self.driver.query(command)
            print(f"Received response: '{q_response.strip()}'")
            return q_response.strip()

        except pyvisa.errors.VisaIOError as e:
            print(f"VISA I/O Error during command '{command.strip()}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred while sending command: {e}")
        return None

# Main execution block
if __name__ == "__main__":
    # Instantiate the GCode_Plugin
    gcode_handler = GCode_Plugin()

    # Attempt to connect to the found device
    gcode_handler.connect()

    # If connected, send an example G-code command
    if gcode_handler.driver:
        # Example: Request current position from a 3D printer
        response = gcode_handler.send_gcode_command("M114")
        if response:
            print(f"Final processed response: {response}")

        # Example: Move 10 steps along the Y-axis (G0 for rapid move, G1 for controlled move)
        # Choose G0 or G1 based on your device's expected behavior.
        # G0 is typically for rapid, non-extruding moves.
        # G1 is for controlled, linear moves, often with extrusion (F parameter for feedrate).
        move_command = "G0 Y50"
        print(f"\nAttempting to send move command: '{move_command}'")
        
        move_response = gcode_handler.send_gcode_command(move_command)
        if move_response:
            print(f"Move command response: {move_response}")
        else:
            print(f"No response or error received for move command: '{move_command}'")

    # Always ensure to disconnect when done
    gcode_handler.disconnect()
