import h5py
import numpy as np
import re
import datetime

def parse_vna_text_data(filepath):
    """
    Parses the VNA text file and extracts S-parameter data.
    Assumes each block of S-parameter data (separated by a blank line)
    corresponds to a single scan point.
    """
    all_scan_points_data = []
    current_scan_point_data = {}
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                # Skip comment lines
                continue
            
            if not line:
                # Blank line indicates the end of a scan point's data
                if current_scan_point_data:
                    all_scan_points_data.append(current_scan_point_data)
                    current_scan_point_data = {}
                continue
            
            # Regex to capture S-parameter name and values
            # Updated regex to be more flexible with spaces around ':'
            match = re.match(r"([A-Za-z0-9]+)\s*:\s*\[(.*?)\]", line)
            if match:
                s_param_name = match.group(1)
                values_str = match.group(2)
                
                try:
                    # Split values string by comma
                    # Each part should now be a complex number string like '(real+imagj)'
                    complex_string_values = [v.strip() for v in values_str.split(',')]
                    
                    # Convert each complex number string to a complex number
                    complex_values = [complex(v) for v in complex_string_values if v] # 'if v' handles empty strings from trailing commas
                    
                    current_scan_point_data[s_param_name] = np.array(complex_values)
                except ValueError as e:
                    print(f"Error parsing values for {s_param_name}: {e}. Line: {line}")
            else:
                print(f"Warning: Could not parse line: {line}")

    # Add the last scan point if the file doesn't end with a blank line
    if current_scan_point_data:
        all_scan_points_data.append(current_scan_point_data)

    return all_scan_points_data


def convert_to_hdf5(parsed_data, output_filepath="vna_scan_data_parsed.hdf5", original_filepath=""): # Added original_filepath
    """
    Converts the parsed VNA data into an HDF5 file.
    """
    if not parsed_data:
        print("No data to convert to HDF5.")
        return

    # Determine all unique S-parameter names and the number of frequency points
    all_s_param_names = set()
    num_frequencies = 0
    if parsed_data:
        # Assuming the first scan point dictates the S-params and frequencies
        for s_param_name, values in parsed_data[0].items():
            all_s_param_names.add(s_param_name)
            if num_frequencies == 0:
                num_frequencies = len(values)
        
        # Check consistency across all scan points (optional but good practice)
        for i, scan_point in enumerate(parsed_data):
            for s_param_name, values in scan_point.items():
                if len(values) != num_frequencies:
                    print(f"Warning: Inconsistent number of frequency points at scan point {i} for {s_param_name}. Expected {num_frequencies}, got {len(values)}. This might cause errors.")


    num_scan_points = len(parsed_data)

    with h5py.File(output_filepath, 'w') as f:
        scan_group_name = datetime.datetime.now().strftime("scan_%Y%m%d_%H%M%S_parsed")
        scan_group = f.create_group(scan_group_name)
        scan_group.attrs['conversion_time'] = str(datetime.datetime.now())
        # Use the passed original_filepath argument
        scan_group.attrs['original_file'] = original_filepath 

        # You don't have explicit (x,y) coordinates in your text file.
        # If you need them, you'll have to either derive them from the sequence
        # or manually add them. For now, we'll assume a sequential index.
        # You could add a placeholder for future extension.
        
        # Create 's_parameters' group
        s_params_group = scan_group.create_group("s_parameters")
        
        # Create extendable datasets for each S-parameter
        s_param_datasets = {}
        for s_param_name in sorted(list(all_s_param_names)):
            s_param_datasets[f"{s_param_name}_real"] = s_params_group.create_dataset(
                f"{s_param_name}_real", shape=(num_scan_points, num_frequencies), dtype=float
            )
            s_param_datasets[f"{s_param_name}_imag"] = s_params_group.create_dataset(
                f"{s_param_name}_imag", shape=(num_scan_points, num_frequencies), dtype=float
            )

        # Populate the datasets
        for i, scan_point_data in enumerate(parsed_data):
            for s_param_name, complex_values in scan_point_data.items():
                if f"{s_param_name}_real" in s_param_datasets and f"{s_param_name}_imag" in s_param_datasets:
                    s_param_datasets[f"{s_param_name}_real"][i, :] = np.real(complex_values)
                    s_param_datasets[f"{s_param_name}_imag"][i, :] = np.imag(complex_values)
                else:
                    print(f"Warning: S-parameter {s_param_name} found in data but not pre-created in HDF5 datasets. Skipping.")

        print(f"Successfully converted data to HDF5: {output_filepath}")


# --- Main execution ---
if __name__ == "__main__":
    input_file = "vna_data3.txt" # Name of the uploaded file
    output_hdf5_file = "vna_data_converted.hdf5"

    print(f"Parsing {input_file}...")
    parsed_s_param_data = parse_vna_text_data(input_file)
    
    if parsed_s_param_data:
        print(f"Found {len(parsed_s_param_data)} scan points.")
        convert_to_hdf5(parsed_s_param_data, output_hdf5_file)
    else:
        print("No valid S-parameter data found in the input file.")