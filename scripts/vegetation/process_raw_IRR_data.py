import os
import glob
import pandas as pd
from datetime import datetime 

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')
#RAW_DATA_DIR = os.path.join('data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')


# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_EXCEL_DIR = r"D:\Research_Jen\Working"
SOURCE_EXCEL_FILENAME = r"processed_canopy_WORKING_20252709_2117_CSV.csv" # The original Excel file

# --- Define OUTPUT file (where you save the new data TO) ---
today_date_str = datetime.now().strftime('%Y-%d-%m_%H%M')
OUTPUT_DIR = r"D:\Research_Jen\Working" # A new folder for the output
OUTPUT_FILENAME = r"WORKING.csv" # The name for the new output file

#Sets date time format to match the raw data file
DATE_FORMAT_STRING = '%m/%d/%Y %H:%M'

# 2. Split the original filename from its extension
# This turns "working.csv" into "working" and ".csv"
base_name, extension = os.path.splitext(OUTPUT_FILENAME)

# 3. Create the new filename
# This becomes "WORKING_yyyy-dd-mm hhmm.csv"
dated_filename = f"{base_name}_{today_date_str}{extension}"

FINAL_COLUMNS = [
    'Time', 
    'Target', 
    'Sensor Body', 
    'source_file', 
    'well_id', 
    'target_type', 
    'percent_cover', 
    'Notes:'
]

"""
Main function to run the data processing workflow.
"""
# Create the full path for the output file
source_file_path = os.path.join(SOURCE_EXCEL_DIR, SOURCE_EXCEL_FILENAME)
output_file_path = os.path.join(OUTPUT_DIR, dated_filename)

print("--- Starting IRR Data Processing ---")

# 1. Load any existing processed data into a dataframe
print(f"Checking for existing data at: {source_file_path}")
#Initialises a set. A set is a list without repeating elements
processed_dates = set()
existing_df = pd.DataFrame() # Start with an empty DataFrame

if os.path.exists(source_file_path):
    existing_df = pd.read_csv(source_file_path)
    #Removes spaces to help with merging data frames
    existing_df.columns = existing_df.columns.str.strip()
    if 'Time' in existing_df.columns:
        # Create a set of unique dates for efficient lookup
        existing_df['Time'] = pd.to_datetime(existing_df['Time'], format=DATE_FORMAT_STRING)
        processed_dates = set(existing_df['Time'])
        print(f"Loaded {len(existing_df)} existing records with {len(processed_dates)} unique dates.") 
    else: 
        print("No Time column found. Try again")
        exit(0)
#If no file exists at the directory, exit (modify directory before trying again)
else:
    print("No existing data file found. Try again.")
    exit(0)

# 2. Find all raw data files
#Points to RAW_DATA_DIR directory with file names Data Log.. * is a wildcard for any character
search_pattern = os.path.join(RAW_DATA_DIR, 'Data Log*.txt') 
#glob.glob finds all files matching the search pattern and returns them as a list named all_raw_files
all_raw_files = glob.glob(search_pattern)

#If .txt files are not found in directory, exit
if not all_raw_files:
    print("\nNo raw data files found in the source directory.")
    exit(0)

print(f"\nFound {len(all_raw_files)} raw files to scan for new data...")


# 3. Process each file and filter for new rows based on date
#Creates a list to save 
new_data_frames = []
for file_path in all_raw_files:
    filename = os.path.basename(file_path)
    try:
        # Read the raw data file
        temp_df = pd.read_csv(file_path, sep=';')
        #Removes spaces to help with merging data frames
        temp_df.columns = temp_df.columns.str.strip()
        # Add the source_file column for traceability
        temp_df['source_file'] = filename
        
        # Filter the dataframe to include only rows where the 'Time' is NOT in our set of processed dates.
        if 'Time' in temp_df.columns:

            # Check which rows have dates that are already in our processed list.
            # This creates a series of True/False values. 'True' means the date is already in Excel sheet.
            temp_df['Time'] = pd.to_datetime(temp_df['Time'], format=DATE_FORMAT_STRING)
            already_in_excel = temp_df['Time'].isin(processed_dates)
            
            # Invert the mask to find the new rows.
            # We want the rows where 'already_in_excel' is False.
            is_new_data_mask = ~already_in_excel
            
            # Uses boolean indexing/masking (feature of pandas library) to select only the new rows from the DataFrame.
            new_rows_df = temp_df[is_new_data_mask]

        else:
            print(f"  - Warning: 'Time' column not found in {filename}. Skipping file.")
            continue # Move to the next file
        
        #Checks if data frame is not empty (if there are new dates)
        if not new_rows_df.empty:
            print(f" - Found {len(new_rows_df)} new records in '{filename}'.")
            #adds all new rows of data found with unique dates
            new_data_frames.append(new_rows_df)

    except Exception as e:
        print(f"  - Warning: Could not process file {filename}. Error: {e}")


# 4. If there are no new rows across all files, exit
if not new_data_frames:
    print("\nNo new data found in any of the files. Your data is already up-to-date.")
    exit(0)

# 5. Else combine the new data and append it to the existing data
new_data_df = pd.concat(new_data_frames, ignore_index=True)

# Combine the original dataframe with the newly found rows
updated_df = pd.concat([existing_df, new_data_df], ignore_index=True)

# Ensure the final DataFrame has all the correct columns in the correct order
updated_df = updated_df.reindex(columns=FINAL_COLUMNS)

# Write to the OUTPUT path
updated_df.to_csv(output_file_path, index=False)

print(f"\nSuccessfully added {len(new_data_df)} new records.")
print(f"Total records are now {len(updated_df)}.")
print(f"Updated data saved to: {output_file_path}")

print("--- Processing Complete ---")
