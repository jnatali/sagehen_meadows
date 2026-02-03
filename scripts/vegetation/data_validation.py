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
        # ('_', 2) adjusted to account for 'TC_CORRECTED_' prefix
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

    # Clean target type for filtering
    if 'target_type' in existing_df.columns:
        existing_df['type_clean'] = existing_df['target_type'].astype(str).str.strip().str.lower()
    else:
        print("\nERROR: The column 'target_type' was not found in the dataset.")
        print("This column is required to filter for plant data. Exiting program.")
        exit(0)

    #Filter out the row that has no associated well-id 
    bad_well_name = "Patch 1 m of well w/o bare ground"
    existing_df = existing_df[(existing_df['well_id'] == 'EHT-XA5S') | (existing_df['well_id'] == 'KHF-1')]

    #print(f"Removed entry: '{bad_well_name}'")

    # CONVERT TIME 
    # We strictly tell Python the format is Month/Day/Year Hour:Minute
    # errors='coerce' means if there is a bad date, turn it into NaT (Not a Time) instead of crashing
    existing_df['Time'] = pd.to_datetime(existing_df['Time'], errors='coerce')

    # Drop any rows where the time couldn't be converted (just in case)
    existing_df = existing_df.dropna(subset=['Time'])
    
    # Ensure numeric columns are actually numbers
    existing_df['percent_cover'] = pd.to_numeric(existing_df['percent_cover'], errors='coerce')
    existing_df['Target'] = pd.to_numeric(existing_df['Target'], errors='coerce')

    # ---------------------------------------------------------
    # FILTER FOR PLANTS ONLY (AND AVERAGE BY 2-DAY INTERVALS)
    # ---------------------------------------------------------
    print("Processing Plant Data (All wells combined)...")
    plant_df = existing_df[existing_df['type_clean'] == 'plant'].copy()

    # We use pd.Grouper to define the 2-day window on the 'Time' column
    # Averaging percent_cover and Target
    plant_agg = plant_df.groupby(pd.Grouper(key='Time', freq='2D')).agg({
        'percent_cover': 'mean',
        'Target': 'mean'
    }).dropna()

    # ---------------------------------------------------------
    # FILTER FOR THATCH/BARE-THATCH (AND AVERAGE BY 2-DAY INTERVALS)
    # ---------------------------------------------------------
    print("Processing Thatch Data (All wells combined)...")
    thatch_types = ['thatch', 'bare-thatch']
    thatch_df = existing_df[existing_df['type_clean'].isin(thatch_types)].copy()

    # Averaging only Target for thatch
    thatch_agg = thatch_df.groupby(pd.Grouper(key='Time', freq='2D')).agg({
        'Target': 'mean'
    }).dropna()

    # ---------------------------------------------------------
    # -- CREATE PLOT --
    # ---------------------------------------------------------
    if not plant_agg.empty and not thatch_agg.empty:
        
        # Create figure and primary axis (for Temperature)
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Plot Corrected Tc for Plants (Green)
        line1 = ax1.plot(plant_agg.index, plant_agg['Target'], 
                 label='Plant Temp ($T$)', color='green', marker='o', linestyle='-')
        
        # Plot Corrected Tc for Thatch (Brown)
        line2 = ax1.plot(thatch_agg.index, thatch_agg['Target'], 
                 label='Thatch Temp ($T$)', color='brown', marker='s', linestyle='-')

        ax1.set_xlabel("Date/Time")
        ax1.set_ylabel("Temperature (°C)", color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.grid(True, alpha=0.3)

        # Create secondary axis (for Percent Cover)
        ax2 = ax1.twinx()
        
        # Plot Percent Cover (Blue Dashed)
        line3 = ax2.plot(plant_agg.index, plant_agg['percent_cover'], 
                 label='Plant Cover %', color='tab:blue', marker='^', linestyle='--', alpha=0.7)
        
        ax2.set_ylabel("Mean Percent Cover (%)", color='tab:blue')
        ax2.tick_params(axis='y', labelcolor='tab:blue')
        ax2.set_ylim(0, 105) # Fix scale to 0-100%

        # Combine legends from both axes
        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')

        plt.title(f"KHF-1 and EHT-XA5A: Plant T, Thatch T, and Cover %")

        # Format the X-Axis dates nicely
        plt.gcf().autofmt_xdate() # Auto-rotates dates to fit better

        # -- SAVE AS EPS --
        plot_filename = "Data validation for KHF-1 and EHT-XA5A.eps"
        save_path = os.path.join(OUTPUT_DIR, plot_filename)
        plt.savefig(save_path, format='eps', bbox_inches='tight')
        plt.close()

        print(f"All plots saved as .eps to {OUTPUT_DIR}")
        print(f"Generated: {plot_filename}")
        
    else:
        print("Error: Insufficient data for Plants or Thatch to generate combined plot.")

else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")
    exit(0)