#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESS RAW INFRARED RADIOMETER FIELD DATA SCRIPT
Created on 10 October 2025
@author: kara-leah smittle, jennifer natali

Takes RAW .txt data files from Apogee IRR instrument,
as collected in the field, to build a single csv file
of all observations. This allows data entry from field notes
to associate each observation with a groundwater well_id
and patch type, based on the timestamp of the data entry.

For details on how the data and processing steps for this script
were defined, see github issue:
    https://github.com/jnatali/sagehen_meadows/issues/19

"""

import os
import glob
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt

# --- Configuration ---
# Define the relative paths from the script's location in 'scripts/'
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')


# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')


# 3. Base name of the files to search for
SOURCE_FILE_PATTERN = "WORKING_*.csv"

OUTPUT_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
OUTPUT_FILENAME = "WORKING.csv" # The name for the new output file

OUTPUT_GRAPH_DIR = os.path.join('..', '..', 'results', 'plots', 'vegetation', 'canopy_temp')

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

#Sets date time format for all files
DATE_FORMAT_STRING = '%m/%d/%Y %H:%M'

#Validate final columns
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

"""
Main function to run the data processing workflow.
"""

print("--- Starting IRR Data Processing ---")

# Define a search pattern that matches ..', '..', 
# 'data', 'field_observations', 'vegetation', 'canopy_temp' + "WORKING_*.csv"
# * is a wildcard for any character
print(f"Searching for most recent source file in: {SOURCE_DIR}")
search_pattern = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
#glob.glob finds all files matching the search pattern and returns them as a list
#the list is all WORKING csv files 
list_of_files = glob.glob(search_pattern)

##Searching for the most recent CSV file##

#Initialises a set. A set is a list without repeating elements
processed_dates = set()
# Start with an empty DataFrame
existing_df = pd.DataFrame() 
#If files were loaded that matched the search pattern (directory_WORKING)
if list_of_files:
    # Compares the date string in the name based on values returned from function specified by key=
    #saves the most recent file path to variable
    source_file_path = max(list_of_files, key=get_date_from_filename)
    
    print(f"Loading most recent source file (by name): {os.path.basename(source_file_path)}")

    #loads most recent csv file to a data frame
    existing_df = pd.read_csv(source_file_path)

    #Removes spaces from column names to help with validating data
    #.str unlocks string-specific methods for an entire column (or index) at once
    existing_df.columns = existing_df.columns.str.strip()
    
    #Checks for duplicate Time Target combinations in the most recent csv file

    if 'Time' in existing_df.columns and 'Target' in existing_df.columns:

        # Standardize Time format
        existing_df['Time'] = pd.to_datetime(existing_df['Time'], format=DATE_FORMAT_STRING)

        # Round the Target column to 4 decimal places to ensure consistent matching
        existing_df['Target'] = existing_df['Target'].round(4)

        # Count how many rows we have before cleaning
        rows_before = len(existing_df)

        #A list of True/False
        #True if row is a duplicate
        #False is original
        duplicate_mask = existing_df.duplicated(subset=['Time', 'Target'], keep='first')
        
        # Create a dataframe containing ONLY the bad rows
        duplicates_df = existing_df[duplicate_mask]

        # 2. Drop Duplicates
        # subset=['Time', 'Target'] tells Python: "Only consider rows duplicates if 
        # BOTH Time AND Target are identical."
        # keep='first' keeps the top row and deletes the rest.
        existing_df = existing_df.drop_duplicates(subset=['Time', 'Target'], keep='first')

        # Count how many rows we have after cleaning       
        rows_after = len(existing_df)
        duplicates_removed = rows_before - rows_after

        if duplicates_removed > 0:
            print(f"  -> Cleaned: Removed {duplicates_removed} duplicate rows from the original source file.")
        
        # Create a set of tuples (Time, Target) for efficient lookup
        # zip() pairs the two columns together row by row
        processed_signatures = set(zip(existing_df['Time'], existing_df['Target']))
        
        print(f"Loaded {len(existing_df)} existing records.") 
    else: 
        print("Required columns (Time, Target) not found. Try again")
        exit(0)
#If no file exists at the directory, exit (modify directory before trying again)
else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")
    exit(0)


#Find all raw data files
# Define a search pattern that matches '..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW' + "Data Log*.csv"
# * is a wildcard for any character
search_pattern_raw = os.path.join(RAW_DATA_DIR, 'Data Log*.txt') 
#glob.glob finds all files matching the search pattern and returns them as a list named all_raw_files
all_raw_files = glob.glob(search_pattern_raw)

#If .txt files are not found in directory, exit
if not all_raw_files:
    print("\nNo raw data files found in the source directory.")
    exit(0)

print(f"\nFound {len(all_raw_files)} raw files to scan for new data...")


#Check contents of all raw data file for new date / target combinations

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
        
        if 'Time' in temp_df.columns and 'Target' in temp_df.columns:

            # 1. Standardize the Time format in the temporary dataframe
            temp_df['Time'] = pd.to_datetime(temp_df['Time'], format=DATE_FORMAT_STRING)
            
            # 2. Round Target to match the existing data precision
            temp_df['Target'] = temp_df['Target'].round(4)

            # 3. Create the signature tuples for the incoming data
            current_signatures = pd.Series(zip(temp_df['Time'], temp_df['Target']))

            # 4. Check which rows have signatures that are already in our processed set.
            already_in_csv = current_signatures.isin(processed_signatures)
            
            # 5. Invert the mask to find the new rows
            is_new_data_mask = ~already_in_csv
            
            # 6. Select only the new rows
            new_rows_df = temp_df[is_new_data_mask]

        #Appends failed files to list for later file
        else:
            print(f"  - Warning: 'Time' or 'Target' column not found in {filename}. Skipping file.")
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
if failed_files: 
    print(f"\nFound {len(failed_files)} problematic file(s) that could not be processed.")
    
    # Create the fail file path
    fail_filename = f"fail_{today_date_str}.csv"
    fail_file_path = os.path.join(OUTPUT_DIR, fail_filename)
    
    # Convert list to DataFrame with a single column name 'failed_filename' for easy CSV writing
    fail_df = pd.DataFrame(failed_files, columns=['failed_filename'])
    
    # Save to CSV
    fail_df.to_csv(fail_file_path, index=False)
    print(f" - A list of failed files has been saved to: {fail_file_path}")


#Checks if there are new entries to add to the csv file
#If not, checks if there are duplicates to remove from the original csv file
#Saves original csv file without duplicates
#Saves duplicates removed to a seperate file 
if not new_data_frames:
    print("\nNo new data found in any of the files. Your data is already up-to-date.")
    if duplicates_removed > 0: 
        print("\nCreating new file without duplicates")
        existing_df.to_csv(output_file_path, index=False)
        dated__duplicate_filename = f"duplicate_{today_date_str}.csv"
        duplicate_file_path = os.path.join(OUTPUT_DIR,dated__duplicate_filename)
        duplicates_df.to_csv(duplicate_file_path, index = False)
else:
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

print("--- Starting Plotting ---")

#Plotting

# FILTER FOR PLANTS ONLY
if 'target_type' in existing_df.columns:
    plant_df = existing_df[existing_df['target_type'].astype(str).str.lower() == 'plant'].copy()
else:
    print("\nERROR: The column 'target_type' was not found in the dataset.")
    print("This column is required to filter for plant data. Exiting program.")
    exit(0)

#Filter out the row that has no associated well-id 
bad_well_name = "Patch 1 m of well w/o bare ground"
plant_df = plant_df[plant_df['well_id'] != bad_well_name]

print(f"Removed entry: '{bad_well_name}'")

# CONVERT TIME 
# We strictly tell Python the format is Month/Day/Year Hour:Minute
# errors='coerce' means if there is a bad date, turn it into NaT (Not a Time) instead of crashing
plant_df['Time'] = pd.to_datetime(plant_df['Time'], format='%m/%d/%Y %H:%M', errors='coerce')

# Drop any rows where the time couldn't be converted (just in case)
plant_df = plant_df.dropna(subset=['Time'])

# AVERAGE BY 2-DAY INTERVALS
print("Averaging data into 2-day bins...")

# We use pd.Grouper to define the 2-day window on the 'Time' column
plant_df = plant_df.groupby(['well_id', pd.Grouper(key='Time', freq='2D')], as_index=False)['Target'].mean()

# SORT BY TIME
# Now that Python knows they are dates, this will sort Chronologically (Oldest -> Newest)
plant_df = plant_df.sort_values(by='Time')

# Get unique wells
unique_wells = plant_df['well_id'].unique()
print(f"Found {len(unique_wells)} unique wells to plot.")

# LOOP AND PLOT
for well in unique_wells:
    # Filter for this specific well
    well_data = plant_df[plant_df['well_id'] == well]
    
    if len(well_data) == 0:
        continue

    # -- PARSE ID FOR TITLE --
    try:
        codes, well_number = well.split('-')
        meadow_code = codes[0] 
        plant_code  = codes[1]
        zone_code   = codes[2]
        
        meadow_name = "Kiln" if meadow_code == 'K' else "East"
        plant_name = {"E": "Sedge", "W": "Willow", "H": "Mixed Herbaceous"}.get(plant_code, plant_code)
        zone_name = {"R": "Riparian", "T": "Terrace", "F": "Fan"}.get(zone_code, zone_code)
        
        title_text = f"Well {well}: {meadow_name} - {plant_name} - {zone_name}"
    except:
        title_text = f"Well {well}"

    # -- CREATE PLOT --
    plt.figure(figsize=(10, 6))
    
    # Plot line
    plt.plot(well_data['Time'], well_data['Target'], marker='o', linestyle='-')

    plt.title(title_text)
    plt.xlabel("Date/Time")
    plt.ylabel("Temperature (C)")
    plt.grid(True)
    
    # Format the X-Axis dates nicely
    plt.gcf().autofmt_xdate() # Auto-rotates dates to fit better

    # -- SAVE AS EPS --
    clean_filename = well.replace(" ", "_")
    plot_filename = f"Plot_Well_{clean_filename}.eps"
    save_path = os.path.join(OUTPUT_GRAPH_DIR, plot_filename)
    
    plt.savefig(save_path, format='eps', bbox_inches='tight')
    plt.close()

print(f"All plots saved as .eps to {OUTPUT_DIR}")
