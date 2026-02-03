
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

    # --- NEW STEP: PARSE METADATA FROM WELL ID ---
    # We do this BEFORE grouping so we can group by Meadow/Plant/Zone later
    def parse_well(row):
        try:
            codes = row['well_id'].split('-')[0]
            m_code, p_code, z_code = codes[0], codes[1], codes[2]
            
            meadow = "Kiln" if m_code == 'K' else "East"
            plant = {"E": "Sedge", "W": "Willow", "H": "Mixed Herbaceous"}.get(p_code, p_code)
            zone = {"R": "Riparian", "T": "Terrace", "F": "Fan"}.get(z_code, z_code)
            return pd.Series([meadow, plant, zone])
        except:
            return pd.Series([None, None, None])
            print("No existing source files found. Exiting program.")   
            exit(0)

    print("Parsing well IDs into categories...")
    plant_df[['Meadow', 'Plant', 'Zone']] = plant_df.apply(parse_well, axis=1)
    # Drop any that failed parsing
    plant_df = plant_df.dropna(subset=['Meadow', 'Plant', 'Zone'])

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
    # MODIFICATION: Added Meadow, Plant, Zone to groupby to preserve metadata
    plant_df = plant_df.groupby(['Meadow', 'Plant', 'Zone', 'well_id', pd.Grouper(key='Time', freq='2D')], as_index=False).agg({
        'Target': 'mean',
        'corrected_Tc': 'mean'
    })

    # SORT BY TIME
    # Now that Python knows they are dates, this will sort Chronologically (Oldest -> Newest)
    plant_df = plant_df.sort_values(by='Time')

    # -- PLOT AGGREGATES --
    print("Generating aggregate plots...")
    
    # Ensure output dir exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. Plot East vs Kiln means over time (with all data shown)
    plt.figure(figsize=(10, 6))
    
    colors = {'East': 'blue', 'Kiln': 'red'}
    
    for meadow in ['East', 'Kiln']:
        # Filter
        subset = plant_df[plant_df['Meadow'] == meadow]
        
        # Plot ALL DATA (Scatter with transparency)
        plt.scatter(subset['Time'], subset['corrected_Tc'], 
                    label=f'{meadow} (All Data)', color=colors[meadow], alpha=0.3, s=15)
        
        # Plot MEAN (Line)
        # We group by Time again to get the average across ALL wells in that meadow
        mean_data = subset.groupby('Time', as_index=False)['corrected_Tc'].mean()
        plt.plot(mean_data['Time'], mean_data['corrected_Tc'], 
                 label=f'{meadow} (Mean)', color=colors[meadow], linewidth=2.5)

    plt.title("Canopy Temperature: East vs Kiln Meadows")
    plt.ylabel("Temperature (C)")
    plt.xlabel("Date")
    plt.legend()
    plt.grid(True, alpha=0.5)
    plt.gcf().autofmt_xdate()
    
    save_path = os.path.join(OUTPUT_DIR, f"Aggregate_East_vs_Kiln_{today_date_str}.eps")
    plt.savefig(save_path, format='eps', bbox_inches='tight')
    plt.close()
    print(f"Saved East vs Kiln plot.")

    # 2. Plot Sedge vs Willow vs Mixed Herbaceous (Multi-plot)
    # Create a subplot with 3 columns, sharing Y axis for comparison
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
    plant_types = ['Sedge', 'Willow', 'Mixed Herbaceous']
    
    # Calculate global min/max for y-axis limits so they look nice
    y_min = plant_df['corrected_Tc'].min() - 2
    y_max = plant_df['corrected_Tc'].max() + 2

    for i, p_type in enumerate(plant_types):
        ax = axes[i]
        subset = plant_df[plant_df['Plant'] == p_type]
        
        # Plot All Data
        ax.scatter(subset['Time'], subset['corrected_Tc'], 
                   color='green', alpha=0.2, s=15, label='Individual Wells')
        
        # Plot Mean
        if not subset.empty:
            mean_data = subset.groupby('Time', as_index=False)['corrected_Tc'].mean()
            ax.plot(mean_data['Time'], mean_data['corrected_Tc'], 
                    color='darkgreen', linewidth=2.5, label='Mean')
        
        ax.set_title(p_type)
        ax.set_xlabel("Date")
        if i == 0:
            ax.set_ylabel("Temperature (C)")
        
        ax.set_ylim(y_min, y_max)
        ax.grid(True, alpha=0.5)
        # Handle date formatting for subplots
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle("Canopy Temperature by Plant Type")
    plt.tight_layout()
    
    save_path = os.path.join(OUTPUT_DIR, f"Aggregate_PlantTypes_{today_date_str}.eps")
    plt.savefig(save_path, format='eps', bbox_inches='tight')
    plt.close()
    print(f"Saved Plant Types plot.")

    # 3. Plot Riparian vs Terrace vs Fan (Multi-plot)
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
    zones = ['Riparian', 'Terrace', 'Fan']
    
    for i, zone in enumerate(zones):
        ax = axes[i]
        subset = plant_df[plant_df['Zone'] == zone]
        
        # Plot All Data
        ax.scatter(subset['Time'], subset['corrected_Tc'], 
                   color='purple', alpha=0.2, s=15, label='Individual Wells')
        
        # Plot Mean
        if not subset.empty:
            mean_data = subset.groupby('Time', as_index=False)['corrected_Tc'].mean()
            ax.plot(mean_data['Time'], mean_data['corrected_Tc'], 
                    color='indigo', linewidth=2.5, label='Mean')
        
        ax.set_title(zone)
        ax.set_xlabel("Date")
        if i == 0:
            ax.set_ylabel("Temperature (C)")
            
        ax.set_ylim(y_min, y_max)
        ax.grid(True, alpha=0.5)
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle("Canopy Temperature by Zone")
    plt.tight_layout()
    
    save_path = os.path.join(OUTPUT_DIR, f"Aggregate_Zones_{today_date_str}.eps")
    plt.savefig(save_path, format='eps', bbox_inches='tight')
    plt.close()
    print(f"Saved Zones plot.")

    print(f"All aggregate plots saved as .eps to {OUTPUT_DIR}")
else:
    print(f"Error: No existing source files found matching '{search_pattern}'. Exiting program.")

    exit(0)