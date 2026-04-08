import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import math

# Define Source File
OUTPUT_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil','Update')
OUTPUT_FILE_PATTERN = "soil_survey_at_wells.csv"
output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE_PATTERN)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

# Define Source File
SOURCE_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil')
SOURCE_FILE_PATTERN = "soil_survey_at_wells.csv"
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)

print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

word_to_code_mapping = {
    'Coarse Sand': 'COS',
    'Sand': 'S',
    'Fine Sand': 'FS',
    'Very Fine Sand': 'VFS',
    'Loamy Coarse Sand': 'LCOS',
    'Loamy Sand': 'LS',
    'Loamy Fine Sand': 'LFS',
    'Loamy Very Fine Sand': 'LVFS',
    'Coarse Sandy Loam': 'COSL',
    'Sandy Loam': 'SL',
    'Fine Sandy Loam': 'FSL',
    'Very Fine Sandy Loam': 'VFSL',
    'Loam': 'L',
    'Silt Loam': 'SIL',
    'Silt': 'SI',
    'Sandy Clay Loam': 'SCL',
    'Clay Loam': 'CL',
    'Silty Clay Loam': 'SICL',
    'Sandy Clay': 'SC',
    'Silty Clay': 'SIC',
    'Clay': 'C'
}

gravel_size_map = {
    # General, Very, and Extremely Gravelly (
    'GR': '>2 - 76 mm', 'VGR': '>2 - 76 mm', 'XGR': '>2 - 76 mm',
    'GRV': '>2 - 76 mm', 'GRX': '>2 - 76 mm',
    
    # Fine Gravelly
    'FGR': '>2 - 5 mm', 'GRF': '>2 - 5 mm',
    
    # Medium Gravelly
    'MGR': '>5 - 20 mm', 'GRM': '>5 - 20 mm',
    
    # Coarse Gravelly
    'CGR': '>20 - 76 mm', 'GRC': '>20 - 76 mm'
}

gravel_amount_map = {
    # Standard Gravelly (15-35%)
    'GR': '>=15% to <35%', 'FGR': '>=15% to <35%', 'MGR': '>=15% to <35%', 
    'CGR': '>=15% to <35%', 'GRF': '>=15% to <35%', 'GRM': '>=15% to <35%', 'GRC': '>=15% to <35%',
    
    # Very Gravelly (35-60%)
    'VGR': '>=35% to <60%', 'GRV': '>=35% to <60%',
    
    # Extremely Gravelly (60-90%)
    'XGR': '>=60% to <90%', 'GRX': '>=60% to <90%'
}

#Function to check for 'G' and extract the info
def extract_gravel_info(subclass_str):
    # Return empty values if the row is empty (NaN)
    if pd.isna(subclass_str):
        return pd.Series([None, None])
    
    # Split by comma in case there are still multiple items 
    words = [word.strip().upper() for word in subclass_str.split(',')]
    
    # Check each word to see if it contains 'G' and exists in our mapping
    for word in words:
        if 'G' in word and word in gravel_size_map:
            # If found, return both the size and the amount
            return pd.Series([gravel_size_map[word], gravel_amount_map[word]])
            
    # Return empty if no gravel codes are found
    return pd.Series([None, None])

df['start depth (cm)'] = (df['start depth (in)'] * 2.54).round(2)
df['stop depth (cm)'] = (df['stop depth (in)'] * 2.54).round(2)

# Split the 'soil texture' column at the first comma and expand into two columns
df[['texture', 'sub-clas']] = df['soil texture'].str.split(',', n=1, expand=True)

#strip any leftover whitespace (e.g., turning " HO" into "HO")
df['texture'] = df['texture'].str.strip()
df['sub-class'] = df['sub-clas'].str.strip()

# This takes the full words in 'soil texture' and creates a new column with the short codes
df['soil texture code'] = df['soil texture'].map(word_to_code_mapping)

# 3. Apply the function to create the two new columns
df[['gravel size', 'gravel amount']] = df['sub-class'].apply(extract_gravel_info)

df.to_csv(output_path, index=False)
print(f"Saved updated data to: {output_path}")


