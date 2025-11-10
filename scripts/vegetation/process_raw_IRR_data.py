import os
import glob
import pandas as pd
from datetime import datetime 

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')


# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')


# 3. Base name of the files to search for
SOURCE_FILE_PATTERN = "WORKING_*.csv"

OUTPUT_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
OUTPUT_FILENAME = "WORKING.csv" # The name for the new output file


# Saved current date/time in (Year-Month-Day_Hour_Minute) format.
today_date_str = datetime.now().strftime('%Y-%m-%d_%H%M')

# 2. Split the original filename from its extension
# This turns "working.csv" into "working" and ".csv"
base_name, extension = os.path.splitext(OUTPUT_FILENAME)

# 3. Create the new filename
# This becomes "WORKING_yyyy-mm-dd_hhmm.csv"
dated_filename = f"{base_name}_{today_date_str}{extension}"


#Sets date time format to match the raw data file
DATE_FORMAT_STRING = '%m/%d/%Y %H:%M'

#Ensures column names are preserved in source .csv file
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

# function to get the date string from a filename 
def get_date_from_filename(file_path):
    """
    Extracts the 'YYYY-MM-DD_HHMM' string from a filename 
    like 'WORKING_YYYY-MM-DD_HHMM.csv' for sorting.
    """
    try:
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        # Splits 'WORKING_2025-11-09_1530' into ['WORKING', '2025-11-09_1530']
        # and returns the date part.
        #Note the importance of saving file with _
        return name_without_ext.split('_', 1)[1]
    except:
        # If the file is not named correctly (e.g., 'WORKING.csv'),
        # return an empty string so it's not chosen as the max.
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Exiting.")
        exit(0)

"""
Main function to run the data processing workflow.
"""

# Create the full path for the new output file
output_file_path = os.path.join(OUTPUT_DIR, dated_filename)

print("--- Starting IRR Data Processing ---")

# Define a search pattern that matches ..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp' + "WORKING_*.csv"
# * is a wildcard for any character
print(f"Searching for most recent source file in: {SOURCE_DIR}")
search_pattern = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
#glob.glob finds all files matching the search pattern and returns them as a list
list_of_files = glob.glob(search_pattern)


#Initialises a set. A set is a list without repeating elements
processed_dates = set()
# Start with an empty DataFrame
existing_df = pd.DataFrame() 

#If files were loaded that matched the search pattern
if list_of_files:
    # Compares the date string in the name based on values returned from function specified by key=
    #saves the most recent file path to variable
    source_file_path = max(list_of_files, key=get_date_from_filename)
    
    print(f"Loading most recent source file (by name): {os.path.basename(source_file_path)}")
    
    existing_df = pd.read_csv(source_file_path)
    #Removes spaces to help with merging data frames
    existing_df.columns = existing_df.columns.str.strip()
    
    if 'Time' in existing_df.columns:
        # Create a set of unique dates for efficient lookup
        existing_df['Time'] = pd.to_datetime(existing_df['Time'], format=DATE_FORMAT_STRING)
        #set only keeps unique dates from 'Time' column
        processed_dates = set(existing_df['Time'])
        print(f"Loaded {len(existing_df)} existing records with {len(processed_dates)} unique dates.") 
    else: 
        print("No Time column found. Try again")
        exit(0)
#If no file exists at the directory, exit (modify directory before trying again)
else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")
    exit(0)


#Find all raw data files
# Define a search pattern that matches '..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW' + "Data Log*.csv"
# * is a wildcard for any character
search_pattern_raw = os.path.join(RAW_DATA_DIR, 'Data Log*.txt') # Changed variable name to avoid conflict
#glob.glob finds all files matching the search pattern and returns them as a list named all_raw_files
all_raw_files = glob.glob(search_pattern_raw)

#If .txt files are not found in directory, exit
if not all_raw_files:
    print("\nNo raw data files found in the source directory.")
    exit(0)

print(f"\nFound {len(all_raw_files)} raw files to scan for new data...")


#Process each file and filter for new rows based on date
#Creates a list to save 
new_data_frames = []
failed_files = []
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
            # This creates a series of True/False values. 'True' means the date is already in csv
            temp_df['Time'] = pd.to_datetime(temp_df['Time'], format=DATE_FORMAT_STRING)
            already_in_csv = temp_df['Time'].isin(processed_dates)
            
            # Invert the mask to find the new rows.
            # We want the rows where 'already_in_excel' is False.
            is_new_data_mask = ~already_in_csv
            
            # Uses boolean indexing/masking (feature of pandas library) to select only the new rows from the DataFrame.
            new_rows_df = temp_df[is_new_data_mask]

        else:
            print(f"  - Warning: 'Time' column not found in {filename}. Skipping file.")
            failed_files.append(filename)
            continue # Move to the next file
        
        #Checks if data frame is not empty (if there are new dates)
        if not new_rows_df.empty:
            print(f" - Found {len(new_rows_df)} new records in '{filename}'.")
            #adds all new rows of data found with unique dates
            new_data_frames.append(new_rows_df)

    except Exception as e:
        print(f"  - Warning: Could not process file {filename}. Error: {e}")
        failed_files.append(filename)

#If there were any problematic files, save their names to a fail file
if failed_files: # Checks if the list is not empty
    print(f"\nFound {len(failed_files)} problematic file(s) that could not be processed.")
    
    # Create the fail file path
    fail_filename = f"fail_{today_date_str}.csv"
    fail_file_path = os.path.join(OUTPUT_DIR, fail_filename)
    
    # Convert list to DataFrame with a single column name 'failed_filename' for easy CSV writing
    fail_df = pd.DataFrame(failed_files, columns=['failed_filename'])
    
    # Save to CSV
    fail_df.to_csv(fail_file_path, index=False)
    print(f" - A list of failed files has been saved to: {fail_file_path}")


#If there are no new rows across all files, exit
if not new_data_frames:
    print("\nNo new data found in any of the files. Your data is already up-to-date.")
    exit(0)

#Else combine the new data and append it to the existing data
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