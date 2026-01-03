import os
import glob
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
#RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')
RAW_DATA_DIR = r"D:\Research_Jen\canopy_temp_RAW_2025_1108_final-20251108T221628Z-1-001\canopy_temp_RAW_2025_1108_final"
#PROCESSED_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
#PROCESSED_DATA_DIR = r"D:\Research_Jen"
#PROCESSED_FILENAME = r"processed_canopy_temp (Copy).xlsx"

# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_DIR = r"D:\Research_Jen\Working"
#SOURCE_EXCEL_FILENAME = r"processed_canopy_WORKING_20252709_2117_CSV.csv" # The original Excel file

# 3. Base name of the files to search for
SOURCE_FILE_PATTERN = "WORKING_*.csv"

# --- Define OUTPUT file (where you save the new data TO) ---
OUTPUT_DIR = r"D:\Research_Jen\Working" # A new folder for the output
OUTPUT_FILENAME = r"WORKING.csv" # The name for the new output file

# Saved current date/time in (Year-Month-Day_Hour_Minute) format.
today_date_str = datetime.now().strftime('%Y-%m-%d_%H%M')

# 2. Split the original filename from its extension
# This turns "working.csv" into "working" and ".csv"
base_name, extension = os.path.splitext(OUTPUT_FILENAME)

# 3. Create the new filename
# This becomes "WORKING_yyyy-dd-mm hhmm.csv"
dated_filename = f"{base_name}_{today_date_str}{extension}"

# Create the full path for the new output file
output_file_path = os.path.join(OUTPUT_DIR, dated_filename)

# function to get the date string from a filename 
def get_date_from_filename(file_path):
    """
    Extracts the 'YYYY-MM-DD_HHMM' string from a filename 
    like 'WORKING_YYYY-MM-DD_HHMM.csv' for sorting.
    """
    try:
        base_name = os.path.basename(file_path)
        #discards the file extension in the filename
        name_without_ext = os.path.splitext(base_name)[0]

        # Splits 'WORKING_2025-11-09_1530' into ['WORKING', '2025-11-09_1530']
        # and returns the date part.
         # ('_', 1) uses underscore as the breaking point and stops splitting after it finds the 1st underscore
        return name_without_ext.split('_', 1)[1]
       
    except:
        # If the file is not named correctly (e.g., 'WORKING.csv'),
        # exit and try again
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Exiting.")
        exit(0)


print(f"Searching for most recent source file in: {SOURCE_DIR}")
search_pattern = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
#glob.glob finds all files matching the search pattern and returns them as a list
#the list is all WORKING csv files 
list_of_files = glob.glob(search_pattern)

if list_of_files:
    # Compares the date string in the name based on values returned from function specified by key=
    #saves the most recent file path to variable
    source_file_path = max(list_of_files, key=get_date_from_filename)
    
    print(f"Loading most recent source file (by name): {os.path.basename(source_file_path)}")

    existing_df = pd.read_csv(source_file_path)

    # --- PERCENT COVER CALCULATION ---
    # Only run if there are empty (NaN) cells in the percent_cover column
    if existing_df['percent_cover'].isnull().any():
        print("Empty percent_cover detected. Calculating totals...")

        # Ensure everything is numeric and create a temporary date column
        existing_df['percent_cover'] = pd.to_numeric(existing_df['percent_cover'], errors='coerce')
        existing_df['Temp_Date'] = pd.to_datetime(existing_df['Time']).dt.date

        # Define the 3 categories that are usually pre-filled
        other_cats = ['bare-thatch', 'thatch', 'bare ground']

        # Calculate the sum of 'others' for every well on every day
        # We use .fillna(0) so missing values in 'thatch' don't break the math
        daily_sums = (
            existing_df[existing_df['target_type'].isin(other_cats)]
            .groupby(['well_id', 'Temp_Date' , 'target_type'])['percent_cover'].max()
            .groupby(['well_id', 'Temp_Date']).sum()
            .fillna(0)
        )

        # Function to fill the 'plant' remainder
        def fill_plant(row):
            if pd.isna(row['percent_cover']) and str(row['target_type']).lower() == 'plant':
                others_total = daily_sums.get((row['well_id'], row['Temp_Date']), 0)
                return max(0, 100 - others_total) # Ensures we don't get negative numbers
            return row['percent_cover']

        existing_df['percent_cover'] = existing_df.apply(fill_plant, axis=1)

        # Cleanup and rename for the final file
        existing_df = existing_df.drop(columns=['Temp_Date'])
        
        existing_df.to_csv(output_file_path, index=False)
        print(f"Updated data saved to: {output_file_path}")
else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")
    exit(0)