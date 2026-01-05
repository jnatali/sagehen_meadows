import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime

# --- Configuration ---
SOURCE_DIR = r"D:\Research_Jen\Working"
OUTPUT_DIR = r"D:\Research_Jen\Working"

EMISSIVITY = {
    'plant': 0.97,
    'thatch': 0.95,
    'bare-thatch': 0.95,
    'bare ground': 0.95
}

# function to get the date string from a filename 
def get_date_from_filename(file_path):
    """
    Extracts the 'YYYY-MM-DD_HHMM' string from a filename 
    like 'WORKING_YYYY-MM-DD_HHMM.csv' for sorting.
    """
    try:
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        # Returns the part after the first underscore
        return name_without_ext.split('_', 1)[1]
    except:
        print(f"Warning: Filename '{file_path}' does not match expected pattern. Exiting.")
        exit(0)

# Find the latest file 
list_of_files = glob.glob(os.path.join(SOURCE_DIR, "WORKING_*.csv"))
if not list_of_files:
    print("No working files found. Exiting.")
    exit(0)

latest_file = max(list_of_files, key=get_date_from_filename)
print(f"Processing latest file: {os.path.basename(latest_file)}")
df_original = pd.read_csv(latest_file)

# Saves date and target_type in specicific formats to prevent code failure
df_original['Date'] = pd.to_datetime(df_original['Time']).dt.date
df_original['target_type_lower'] = df_original['target_type'].str.lower().str.strip()

# Average data for each unique well/Date/target_type combo
grouped_averages = df_original.groupby(['well_id', 'Date', 'target_type_lower'], as_index=False).agg({
    'Target': 'mean',
    'percent_cover': 'mean'
})

grouped_averages['f'] = grouped_averages['percent_cover'] / 100.0
grouped_averages['Temp_K'] = grouped_averages['Target'] + 273.15

#Calculate energy for each row
def get_energy(row):
    #get emissivity from dictionary, default to .95 if item doesn't match any list item
    e = EMISSIVITY.get(row['target_type_lower'], 0.95)
    return e * row['f'] * (row['Temp_K']**4)

#get energy for each row in grouped_averages df
grouped_averages['energy_contrib'] = grouped_averages.apply(get_energy, axis=1)

# Sum non-plant energy components per well/day
other_cats = ['thatch', 'bare-thatch', 'bare ground']
noise_lookup = (
    grouped_averages[grouped_averages['target_type_lower'].isin(other_cats)]
    .groupby(['well_id', 'Date'])['energy_contrib']
    .sum()
    .reset_index()
    .rename(columns={'energy_contrib': 'sum_noise'})
)

# Apply Correction to Original Dataframe
df_original = pd.merge(df_original, noise_lookup, on=['well_id', 'Date'], how='left')
df_original['sum_noise'] = df_original['sum_noise'].fillna(0)


def solve_tc(row):
    if row['target_type_lower'] != 'plant':
        return np.nan
        
    e_p = EMISSIVITY['plant']
    f_p = row['percent_cover'] / 100.0
    ts_k_4 = (row['Target'] + 273.15)**4
    
    # Mathematical implementation of Equation (9)
    numerator = ts_k_4 - row['sum_noise']
    denominator = e_p * f_p
    
    # Safety check: Prevent square root of negative numbers
    if numerator > 0 and denominator > 0:
        tc_k = (numerator / denominator)**0.25
        return tc_k - 273.15
    return np.nan

df_original['corrected_Tc'] = df_original.apply(solve_tc, axis=1)
df_original['Tc_Difference'] = df_original['Target'] - df_original['corrected_Tc']

# 5. Save the final file
timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
final_output = os.path.join(OUTPUT_DIR, f"TC_CORRECTED_{timestamp}.csv")

# Clean up temporary processing columns but keep all original columns
cols_to_drop = ['Date', 'target_type_lower', 'sum_noise']
df_original.drop(columns=cols_to_drop).to_csv(final_output, index=False)

print(f"Success! Corrected file saved as: {final_output}")