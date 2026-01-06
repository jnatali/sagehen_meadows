import os
import glob
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt

# --- Configuration ---

# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')

# 3. Base name of the files to search for
SOURCE_FILE_PATTERN = "TC_CORRECTED_*.csv"

# --- Define OUTPUT file (where you save the new graphs TO) ---
OUTPUT_DIR = os.path.join('..', '..', 'results', 'plots', 'vegetation', 'canopy_temp')

# Saved current date/time in (Year-Month-Day_Hour_Minute) format.
today_date_str = datetime.now().strftime('%Y-%m-%d_%H%M')

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
        # Note: adjusted split to index 2 to account for 'TC_CORRECTED_' prefix
        return name_without_ext.split('_', 2)[2]
        
    except:
        # If the file is not named correctly (e.g., 'WORKING.csv'),
        # exit and try again
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Exiting.")
        exit(0)


print(f"Searching for most recent source file in: {SOURCE_DIR}")
search_pattern = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
#glob.glob finds all files matching the search pattern and returns them as a list
#the list is all TC_CORRECTED csv files 
list_of_files = glob.glob(search_pattern)

if list_of_files:
    # Compares the date string in the name based on values returned from function specified by key=
    #saves the most recent file path to variable
    source_file_path = max(list_of_files, key=get_date_from_filename)
    
    print(f"Loading most recent source file (by name): {os.path.basename(source_file_path)}")

    existing_df = pd.read_csv(source_file_path)
    # FILTER FOR PLANTS ONLY
    if 'target_type' in existing_df.columns:
        plant_df = existing_df[existing_df['target_type'].astype(str).str.lower() == 'plant'].copy()
        plant_df['well_id'] = plant_df['well_id'].astype(str).str.strip()
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
    plant_df['Time'] = pd.to_datetime(plant_df['Time'], errors='coerce')

    # Drop any rows where the time couldn't be converted (just in case)
    plant_df = plant_df.dropna(subset=['Time', 'corrected_Tc'])

    # AVERAGE BY 2-DAY INTERVALS
    print("Averaging data into 2-day bins...")

    # We use pd.Grouper to define the 2-day window on the 'Time' column
    # Averaging both Raw Target and Corrected Temperature
    plant_df = plant_df.groupby(['well_id', pd.Grouper(key='Time', freq='2D')], as_index=False).agg({
        'Target': 'mean',
        'corrected_Tc': 'mean'
    })

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

        # Plot Raw Target line (Solid light gray for EPS compatibility)
        plt.plot(well_data['Time'], well_data['Target'], label='Raw Target Temp', color='#C0C0C0', linestyle='--')
        # Plot Corrected line
        plt.plot(well_data['Time'], well_data['corrected_Tc'], label='Corrected $T_c$', marker='o', linestyle='-', color='green')
        plt.title(title_text)
        plt.xlabel("Date/Time")
        plt.ylabel("Temperature (C)")
        plt.legend()
        plt.grid(True)

        # Format the X-Axis dates nicely
        plt.gcf().autofmt_xdate() # Auto-rotates dates to fit better

        # -- SAVE AS EPS --
        clean_filename = well.replace(" ", "_")
        plot_filename = f"Temperature_{clean_filename}.eps"
        save_path = os.path.join(OUTPUT_DIR, plot_filename)
        plt.savefig(save_path, format='eps', bbox_inches='tight')
        plt.close()

    print(f"All plots saved as .eps to {OUTPUT_DIR}")
else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")

    exit(0)
