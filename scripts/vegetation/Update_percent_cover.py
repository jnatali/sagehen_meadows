import os
import glob
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
OUTPUT_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')

# File patterns and naming
SOURCE_FILE_PATTERN = "WORKING_*.csv"
OUTPUT_FILENAME = "WORKING.csv" 

# --- Setup Output Pathing ---
today_date_str = datetime.now().strftime('%Y-%m-%d_%H%M')
base_name, extension = os.path.splitext(OUTPUT_FILENAME)
dated_filename = f"{base_name}_{today_date_str}{extension}"
output_file_path = os.path.join(OUTPUT_DIR, dated_filename)

# --- Functions ---

def get_date_from_filename(file_path):
    """
    Extracts the 'YYYY-MM-DD_HHMM' string from a filename 
    like 'WORKING_YYYY-MM-DD_HHMM.csv' for sorting.
    """
    try:
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        # Splits 'WORKING_2025-11-09_1530' into ['WORKING', '2025-11-09_1530']
        return name_without_ext.split('_', 1)[1]
    except Exception:
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Skipping.")
        return "0000-00-00_0000"

# --- Main Processing ---

print(f"Searching for most recent source file in: {SOURCE_DIR}")
search_pattern = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
list_of_files = glob.glob(search_pattern)

if list_of_files:
    # Find the most recent file based on the timestamp in the name
    source_file_path = max(list_of_files, key=get_date_from_filename)
    print(f"Loading most recent source file: {os.path.basename(source_file_path)}")

    existing_df = pd.read_csv(source_file_path)

    # --- PERCENT COVER CALCULATION ---
    if existing_df['percent_cover'].isnull().any():
        print("Empty percent_cover detected. Calculating plant coverage remainder...")

        # Ensure numeric types and create a temporary date column for grouping
        existing_df['percent_cover'] = pd.to_numeric(existing_df['percent_cover'], errors='coerce')
        existing_df['Temp_Date'] = pd.to_datetime(existing_df['Time']).dt.date

        # Define categories to subtract from 100%
        other_cats = ['bare-thatch', 'thatch', 'bare ground']

        # Calculate the sum of non-plant categories per well per day
        daily_sums = (
            existing_df[existing_df['target_type'].isin(other_cats)]
            .groupby(['well_id', 'Temp_Date', 'target_type'])['percent_cover'].max()
            .groupby(['well_id', 'Temp_Date']).sum()
            .fillna(0)
        )

        def fill_plant(row):
            """Calculates remaining percentage for 'plant' rows."""
            if pd.isna(row['percent_cover']) and str(row['target_type']).lower() == 'plant':
                others_total = daily_sums.get((row['well_id'], row['Temp_Date']), 0)
                return max(0, 100 - others_total)
            return row['percent_cover']

        existing_df['percent_cover'] = existing_df.apply(fill_plant, axis=1)

        # Cleanup temporary column
        existing_df = existing_df.drop(columns=['Temp_Date'])
        
        # Ensure the output directory exists
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        existing_df.to_csv(output_file_path, index=False)
        print(f"Success! Updated data saved to: {output_file_path}")
    else:
        print("No empty percent_cover cells found. No calculations needed.")

else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting.")
    exit(0)
