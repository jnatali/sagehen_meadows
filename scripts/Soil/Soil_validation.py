import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import math

# Define Source File
OUTPUT_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil')
OUTPUT_FILE_PATTERN = "soil_survey_at_wells_update_w_G.csv"
output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE_PATTERN)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

# Define Source File
SOURCE_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil')
SOURCE_FILE_PATTERN = "soil_survey_at_wells_update.csv"
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)

print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

word_to_code_mapping = {
    'coarse sand': 'COS',
    'sand': 'S',
    'fine sand': 'FS',
    'very fine sand': 'VFS',
    'loamy coarse sand': 'LCOS',
    'loamy sand': 'LS',
    'loamy fine sand': 'LFS',
    'loamy very fine sand': 'LVFS',
    'coarse sandy loam': 'COSL',
    'sandy loam': 'SL',
    'fine sandy loam': 'FSL',
    'very fine sandy loam': 'VFSL',
    'loam': 'L',
    'silt loam': 'SIL',
    'silt': 'SI',
    'sandy clay loam': 'SCL',
    'clay loam': 'CL',
    'silty clay loam': 'SICL',
    'sandy clay': 'SC',
    'silty clay': 'SIC',
    'clay': 'C'
}

gravel_size_map = {
    #left end exclusive
    # General, Very, and Extremely Gravelly (>2 - 76 mm)
    'GR': (5, 20), 'VGR': (5, 20), 'XGR': (5, 20),
    'GRV': (5, 20), 'GRX': (5, 20),
    
    # Fine Gravelly (>2 - 5 mm)
    'FGR': (2, 5), 'GRF': (2, 5),
    
    # Medium Gravelly (>5 - 20 mm)
    'MGR': (5, 20), 'GRM': (5, 20),
    
    # Coarse Gravelly (>20 - 76 mm)
    'CGR': (20, 76), 'GRC': (20, 76)
}

gravel_amount_map = {
    #These are all right end exclusive
    # Standard Gravelly (15->35%)
    'GR': (0.15, 0.35), 'FGR': (0.15, 0.35), 'MGR': (0.15, 0.35), 
    'CGR': (0.15, 0.35), 'GRF': (0.15, 0.35), 'GRM': (0.15, 0.35), 'GRC': (0.15, 0.35),
    
    # Very Gravelly (35->60%)
    'VGR': (0.35, 0.60), 'GRV': (0.35, 0.60),
    
    # Extremely Gravelly (60->90%)
    'XGR': (0.60, 0.90), 'GRX': (0.60, 0.90)
}

#Function to check for 'G' and extract the info
def extract_gravel_info(subclass_str):
    # Return empty values if the row is empty (NaN)
    if pd.isna(subclass_str):
        return pd.Series([None, 0])
    
    # Split by comma in case there are still multiple items 
    words = [word.strip().upper() for word in subclass_str.split(',')]
    
    # Check each word to see if it contains 'G' and exists in our mapping
    for word in words:
        if 'G' in word and word in gravel_size_map:
            # If found, return both the size and the amount
            return pd.Series([gravel_size_map[word], gravel_amount_map[word]])
            
    # Return empty if no gravel codes are found
    return pd.Series([None, 0])


# Split the 'soil texture' column at the first comma and expand into two columns
df[['texture', 'sub-class']] = df['soil texture'].str.split(',', n=1, expand=True)

#strip any leftover whitespace 
df['texture'] = df['texture'].str.strip().str.lower()
df['sub-class'] = df['sub-class'].str.strip()

#takes the full words in 'soil texture' and creates a new column with the short codes
df['soil texture code'] = df['texture'].map(word_to_code_mapping)

#Apply the function to create the two new columns
df[['gravel size', 'gravel amount']] = df['sub-class'].apply(extract_gravel_info)

df.to_csv(output_path, index=False)
print(f"Saved updated data to: {output_path}")


