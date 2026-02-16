#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESS RAW INFRARED RADIOMETER FIELD DATA SCRIPT
Created on 10 December 2025
@author: kara-leah smittle, jennifer natali

Takes a single csv file of all canopy temperature observations,
and corrects the calculated temperature based on the measured
patch characteristics and associated emissivity (citations noted 
                                                 in code, for now).

For details on how the data and processing steps for this script
were defined, see github issue:
    https://github.com/jnatali/sagehen_meadows/issues/19

"""

import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime

# --- Configuration ---
# These paths are relative to the script's location (assuming script is in 'scripts/')
RAW_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp', 'RAW')
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
SOURCE_FILE_PATTERN = "TC_CORRECTED_*.csv"

OUTPUT_DIR = os.path.join('..', '..', 'data', 'field_observations', 'vegetation', 'canopy_temp')
OUTPUT_FILENAME = "TC_CORRECTED_.csv" 
OUTPUT_GRAPH_DIR = os.path.join('..', '..', 'results', 'plots', 'vegetation', 'canopy_temp')

# Sources of emissivity estimates from Hillel p 312 and Mira et al 2007
EMISSIVITY = {
    'plant': 0.97, # Jones, 2004, p. 114 says 0.92-0.96; higher if full canopy
                   # Campbell and Norman, 1998, p. 230 says 0.98-0.99 if full
    'thatch': 0.95, # dry leaves
    'bare-thatch': 0.95,
    'bare ground': 0.95 # for dry soil, might be 0.96 if moist
}


# --- Functions ---

def get_date_from_filename(file_path):
    """
    Extracts the 'YYYY-MM-DD_HHMM' string from a filename 
    like 'WORKING_YYYY-MM-DD_HHMM.csv' for sorting.
    """
    try:
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        # Returns the part after the first underscore (e.g., 2023-05-01_1200)
        return name_without_ext.split('_', 1)[1]
    except Exception:
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Skipping.")
        return "0000-00-00_0000"

# --- Main Processing ---

# 1. Find the latest file using the pattern defined in config
list_of_files = glob.glob(os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN))

if not list_of_files:
    print(f"No files matching {SOURCE_FILE_PATTERN} found in {SOURCE_DIR}. Exiting.")
    exit(0)

latest_file = max(list_of_files, key=get_date_from_filename)
print(f"Processing latest file: {os.path.basename(latest_file)}")
df_original = pd.read_csv(latest_file)

# 2. Data Preparation
df_original['Date'] = pd.to_datetime(df_original['Time']).dt.date
df_original['target_type_lower'] = df_original['target_type'].str.lower().str.strip()

# 3. Calculate Averages for Energy Correction
grouped_averages = df_original.groupby(['well_id', 'Date', 'target_type_lower'], as_index=False).agg({
    'Target': 'mean',
    'percent_cover': 'mean'
})

grouped_averages['f'] = grouped_averages['percent_cover'] / 100.0
grouped_averages['Temp_K'] = grouped_averages['Target'] + 273.15

def get_energy(row):
    e = EMISSIVITY.get(row['target_type_lower'], 0.95)
    return e * row['f'] * (row['Temp_K']**4)

grouped_averages['energy_contrib'] = grouped_averages.apply(get_energy, axis=1)

# 4. Sum non-plant energy components (Noise)
other_cats = ['thatch', 'bare-thatch', 'bare ground']
noise_lookup = (
    grouped_averages[grouped_averages['target_type_lower'].isin(other_cats)]
    .groupby(['well_id', 'Date'])['energy_contrib']
    .sum()
    .reset_index()
    .rename(columns={'energy_contrib': 'sum_noise'})
)

# 5. Apply Correction
df_original = pd.merge(df_original, noise_lookup, on=['well_id', 'Date'], how='left')
df_original['sum_noise'] = df_original['sum_noise'].fillna(0)

def solve_tc(row):
    if row['target_type_lower'] != 'plant':
        return np.nan
        
    e_p = EMISSIVITY['plant']
    f_p = row['percent_cover'] / 100.0
    ts_k_4 = (row['Target'] + 273.15)**4
    
    numerator = ts_k_4 - row['sum_noise']
    denominator = e_p * f_p
    
    if numerator > 0 and denominator > 0:
        tc_k = (numerator / denominator)**0.25
        return tc_k - 273.15
    return np.nan

df_original['corrected_Tc'] = df_original.apply(solve_tc, axis=1)
df_original['Tc_Difference'] = df_original['Target'] - df_original['corrected_Tc']

# 6. Save the final file
# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
final_output = os.path.join(OUTPUT_DIR, f"TC_CORRECTED_{timestamp}.csv")

# Clean up temporary columns and save
cols_to_drop = ['Date', 'target_type_lower', 'sum_noise']
df_original.drop(columns=cols_to_drop).to_csv(final_output, index=False)

print(f"Success! Corrected file saved as: {final_output}")

