#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
##########  FIELD SOIL SURVEY DATA PROCESSING SCRIPT  ##########  

This module validates and processes soil profile data for groundwater
wells in Sagehen meadows. Transforms RAW data into "clean" 
data ready for plotting.

This code is under development and follows basic procedural programming,
leverages Pandas DataFrames and csv files with well-defined column names.

NOTE: Assumes that if 'G' is in 'sub-class' column value,
      the content is about gravels. 

Requires X data files:
1. RAW soil profile data

TODOs documented in github repo issue tracking.
- Can we safely change check for 'G' to 'GR' to be more specific?

RECENT UPDATES:
    06/02/2026 JN added a "clean" function to prep data for plotting
                via the R script
    06/01/2026 JN added comments and documentation;
               JN added import from well_utils 
                to leverage process_well_ids() function;

"""
# --- DUNDERS ---
__author__ = 'Kara-Leah Smittle, Jennifer Natali'
__copyright__ = 'Copyright (C) 2026 Riverlab, UC Berkeley'
__license__ = 'NOT Licensed, Private Code under Development, DO NOT DISTRIBUTE'
__maintainer__ = 'Jennifer Natali'
__email__ = 'jennifer.natali@berkeley.edu'
__status__ = 'Development'



# ---- IMPORTS ---
import pandas as pd
#import matplotlib.pyplot as plt
#import seaborn as sns
#import numpy as np
import os
#import math
from pathlib import Path
import sys
import re
import warnings

# Initialize PROJECT_ROOT to allow local project module import
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.groundwater.well_utils import process_well_ids

# ---- INITIALIZE FILE VARIABLES ---

# Define Source File
OUTPUT_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil')
OUTPUT_FILE_PATTERN_VALIDATED = "soil_survey_VALIDATED.csv"
OUTPUT_FILE_PATTERN_CLEANED = "soil_survey_PROCESSED.csv"

# Define Source File
SOURCE_DIR = os.path.join( '..','..', 'data', 'field_observations', 
                          'soil', 'RAW')
SOURCE_FILE_PATTERN = "soil_survey_RAW.csv"

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
    # These are all right end exclusive
    # Standard Gravelly (15->35%)
    'GR': (0.15, 0.35), 'FGR': (0.15, 0.35), 'MGR': (0.15, 0.35), 
    'CGR': (0.15, 0.35), 'GRF': (0.15, 0.35), 'GRM': (0.15, 0.35), 
    'GRC': (0.15, 0.35),
    
    # Very Gravelly (35->60%)
    'VGR': (0.35, 0.60), 'GRV': (0.35, 0.60),
    
    # Extremely Gravelly (60->90%)
    'XGR': (0.60, 0.90), 'GRX': (0.60, 0.90)
}

# ---- FUNCTIONS ---

def populate_depths_cm(df):
    """
    Fill missing depth values in cm from inch columns.

    Existing cm values are preserved.
    """

    df = df.copy()

    depth_pairs = [
        ("start depth (cm)", "start depth (in)"),
        ("stop depth (cm)", "stop depth (in)")
    ]

    for cm_col, in_col in depth_pairs:

        if cm_col not in df.columns:
            raise ValueError(f"Missing required column: {cm_col}")

        if in_col not in df.columns:
            raise ValueError(f"Missing required column: {in_col}")

        df[cm_col] = pd.to_numeric(df[cm_col], errors="coerce")
        inches = pd.to_numeric(df[in_col], errors="coerce")

        # Fill missing cm values from inches
        missing_cm = df[cm_col].isna() & inches.notna()
        df.loc[missing_cm, cm_col] = inches.loc[missing_cm] * 2.54

        # Warn about rows where neither value exists
        missing_both = df[cm_col].isna() & inches.isna()

        if missing_both.any():
            warnings.warn(
                f"{missing_both.sum()} rows are missing both "
                f"'{cm_col}' and '{in_col}'."
            )

    return df

# Convert gravel amount values
def parse_gravel_amount(x):
    if pd.isna(x):
        return x

    # If already numeric, keep it
    if isinstance(x, (int, float)):
        return x

    x = str(x).strip()

    # Match ranges like "(0.15,0.35)" or "(0.15, 0.35)"
    match = re.match(r'^\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$', x)
    if match:
        return float(match.group(2))  # max value of the range

    # Otherwise treat as a single number
    try:
        return float(x)
    except ValueError:
        return x  # leave unexpected values unchanged

def extract_gravel_info(subclass_str):
    """
    Checks for 'G' and extracts info about gravel size categories

    Parameters: 
    
    Returns:
    """    
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

def clean_for_plotting(df_valid):
    """
    - Filters and renames required columns for plotting: start and stop depth, 
        texture, gravel amount in percent
    - Standardizes values for soil texture and gravel %age
    
    Parameters: full pandas dataframe of raw soils data
    
    Returns: nothing, but outputs two files
        1. a validated .csv with raw data but renamed wells and 
            translated gravel size, gravel percentages
        2. a cleaned .csv with limited columns and standardized values
    """    
    df = df_valid.copy()
    
    df["gravel_amount_percent"] = df["gravel amount"].apply(parse_gravel_amount)
    
    df = df.rename(columns={
        "start depth (cm)": "start_depth_cm",
        "stop depth (cm)": "stop_depth_cm",
        "soil texture code": "soil_texture_code"
    })
    
    desired_cols = [
        "well_id",
        "date",
        "start_depth_cm",
        "stop_depth_cm",
        "soil_texture_code",
        "gravel_amount_percent",
    ]
    
    df = df[[col for col in desired_cols if col in df.columns]]
    
    return df
    
# ---- MAIN PROCEDURES---

# Load files
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)
print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

output_path_validated = os.path.join(OUTPUT_DIR, OUTPUT_FILE_PATTERN_VALIDATED)
output_path_cleaned = os.path.join(OUTPUT_DIR, OUTPUT_FILE_PATTERN_CLEANED)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

# Validate and correct well_ids (well names), also drops invalid well_ids
df = process_well_ids(df,datetime_col="date")
print('\nProcessed well_ids\n')

# Make sure the start and stop depths are all converted to cm
df = populate_depths_cm(df)

# Split the 'soil texture' column at the first comma and expand into two columns
df[['texture', 'sub-class']] = df['soil texture'].str.split(
                                                        ',', n=1, expand=True)
#strip any leftover whitespace 
df['texture'] = df['texture'].str.strip().str.lower()
df['sub-class'] = df['sub-class'].str.strip()

# takes the full words in 'soil texture', creates new column with short codes
df['soil texture code'] = df['texture'].map(word_to_code_mapping)

#Apply the function to create the two new columns
df[['gravel size', 'gravel amount']] = df['sub-class'].apply(extract_gravel_info)

df.to_csv(output_path_validated, index=False)
print(f"\nSaved validated data to: {output_path_validated}\n")

# Clean and save data
df_clean = clean_for_plotting(df)
df_clean.to_csv(output_path_cleaned, index=False)
print(f"\nSaved cleaned data for plotting: {output_path_cleaned}\n")



