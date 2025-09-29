import os
import glob
import pandas as pd
import datetime # <--- Added this new import

# --- Configuration ---
# --- Source 1: Canopy Temp TXT files ---
SOURCE_1_DIR = "/run/media/smittlek/KINGSTON/Research_Jen/canopy_temp_RAW_2025_0919_update-20250220T050912Z-1-001/canopy_temp_RAW_2025_0919_update"
SOURCE_1_PATTERN = "Data Log*.txt"

# --- Source 2: Your Second CSV files ---
SOURCE_2_DIR = "/run/media/smittlek/KINGSTON/Research_Jen"  # <--- UPDATE THIS
SOURCE_2_PATTERN = "processed_canopy_WORKING_20252709_2117_CSV.csv"          # <--- UPDATE THIS
SOURCE_2_SEPARATOR = ","

# --- Output File ---
PROCESSED_DATA_DIR = "/run/media/smittlek/KINGSTON/Research_Jen"

# --- Create a filename with the current date and time ---
# 1. Get the current time.
now = datetime.datetime.now()
# 2. Format it into the string you want (YYYY_MM_DD_HH_MM).
timestamp = now.strftime("%Y_%m_%d_%H_%M")
# 3. Create the final filename.
PROCESSED_FILENAME = f'processed_canopy_temp_{timestamp}.csv'
# --- End of new code for filename ---

# --- Start of the Script ---

processed_file_path = os.path.join(PROCESSED_DATA_DIR, PROCESSED_FILENAME)
print(f"--- Starting Data Processing ---")
# This print statement now shows the new, unique filename for this run.
print(f"Output file will be saved to: {processed_file_path}")

#a set is a list of unique items
processed_pairs = set()
existing_df = pd.DataFrame()

#creates a list of data frames to hold all new data
all_new_data_frames = []

# --- 2. Process Data Source 1 ---
print("\n--- Scanning Source 1: Canopy Temp TXT Logs ---")

search_path_1 = os.path.join(SOURCE_1_DIR, SOURCE_1_PATTERN)
source_1_files = glob.glob(search_path_1)
print(f"Found {len(source_1_files)} files to check in Source 1.")

for file_path in source_1_files:
    filename = os.path.basename(file_path)
    print(f"\n...Processing file: {filename}")
    try:
        temp_df = pd.read_csv(file_path, sep=None, engine='python')
        temp_df['source_file'] = filename
        
        if 'Time' in temp_df.columns and 'Target' in temp_df.columns:
            new_rows_list = []
            
            for index, row in temp_df.iterrows():
                time_value = row['Time']
                target_value = row['Target']
                current_pair_tuple = (time_value, target_value)
                
                # We no longer check against a previous file, so every row is new.
                new_rows_list.append(row)

            if new_rows_list:
                new_rows = pd.DataFrame(new_rows_list)
                print(f" - Found {len(new_rows)} records in this file.")
                all_new_data_frames.append(new_rows)
            else:
                print(" - No records found in this file.")
        else:
            print(f" - Warning: 'Time' or 'Target' column not found in {filename}.")
            
    except Exception as e:
        print(f" - Error processing file {filename}. Error: {e}")

# --- 3. Process Data Source 2 ---
print("\n--- Scanning Source 2: Your Second CSV files ---")
search_path_2 = os.path.join(SOURCE_2_DIR, SOURCE_2_PATTERN)
source_2_files = glob.glob(search_path_2)
print(f"Found {len(source_2_files)} files to check in Source 2.")

for file_path in source_2_files:
    filename = os.path.basename(file_path)
    print(f"\n...Processing file: {filename}")
    try:
        temp_df = pd.read_csv(file_path, sep=SOURCE_2_SEPARATOR)
        temp_df['source_file'] = filename
        
        if 'Time' in temp_df.columns and 'Target' in temp_df.columns:
            new_rows_list = []
            for index, row in temp_df.iterrows():
                # We no longer check against a previous file, so every row is new.
                new_rows_list.append(row)

            if new_rows_list:
                new_rows = pd.DataFrame(new_rows_list)
                print(f" - Found {len(new_rows)} records in this file.")
                all_new_data_frames.append(new_rows)
            else:
                print(" - No records found in this file.")
        else:
            print(f" - Warning: 'Time' or 'Target' column not found in {filename}.")

    except Exception as e:
        print(f" - Error processing file {filename}. Error: {e}")

# --- 4. Combine and Save the Data ---
print("\n--- Finalizing Data ---")

if not all_new_data_frames:
    print("No data found in any source.")
else:
    # We are no longer appending to an old file, just saving the new data.
    updated_df = pd.concat(all_new_data_frames, ignore_index=True)
    
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    updated_df.to_csv(processed_file_path, index=False)
    
    print(f"Successfully saved {len(updated_df)} total records to the new file.")
    
print("\n--- Processing Complete ---")