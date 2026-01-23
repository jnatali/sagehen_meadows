#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESS RAW HYGROCHRON DATA SCRIPT

Created on Thu Jan 22 17:38:22 2026
@author: jennifer natali

Takes RAW .csv data files from iButton hygrochrons
as collected in the field, to build a single csv file
of all Temperature (in C) and Relative Humidity (%) observations. 

Each observation is associated with a timestamp, groundwater well_id
and hygrochron serial number.
"""
## --- IMPORTS ---
# Basic libraries
import os
import glob
from pathlib import Path
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt

## --- INITIALIZE VARIABLES ---

# --- Define SOURCE data directory (where you read existing data FROM) ---
RAW_DATA_DIR = Path(os.path.join('..', '..', 'data', 'field_observations', 'hygrochron', 'RAW'))

# Input (source data) filenames
SOURCE_FILE_PATTERN = "*.csv"


# Output filenames

# Final date time format for all files
#DATE_FORMAT_STRING = '%mm/%dd/%YYY %HH:%MM'

# Final columns
FINAL_COLUMNS = [
    'datetime', 
    'well_id', 
    'hygrochron_id',
    'RH_pct',
    'temperature_C',
    'notes', 
    'source_file'
]

## --- FUNCTIONS ---
def process_csv(csv_path):
    
    # csv header row starts at Row 20
    df = pd.read_csv(csv_path, sep=",", skiprows=19, index_col=0)
        
    # combine index date and Date/Time column (which is only the time)
    date = df.index
    df = df.reset_index(drop=True)
    df["datetime"] = date.astype(str)+" "+df["Date/Time"].astype(str)
    df = df.drop("Date/Time", axis=1)
  
    # extract IDs from filename
    parts = csv_path.stem.split("_")
    well_id = parts[0] # string preceding the first _
    hygrochron_id = parts[1] # string between the 1st and 2nd _
    
    # assign ID values to appropriate column names
    df["well_id"] = well_id
    df["hygrochron_id"] = hygrochron_id
    df["source_file"] = csv_path.name
    
    # Initialize measurement columns
    df["RH_pct"] = pd.NA
    df["temperature_C"] = pd.NA

    # Assign based on Unit
    unit = df["Unit"].iloc[0]
    if unit == "%RH":
        df["RH_pct"] = df["Value"]
    elif unit == "C":
        df["temperature_C"] = df["Value"]
    else:
        raise ValueError(f"Unexpected unit '{unit}' in {csv_path.name}")
    
    return df.reindex(columns=FINAL_COLUMNS)


## --- MAIN PROCESSING ---
# 0. Create a dataframe to contain all RH/Temp entries
hygro_data = []

# 1. Loop thru csv's in RAW_DIR to build a single dataframe
for csv_path in RAW_DATA_DIR.glob(SOURCE_FILE_PATTERN):
    
    # append processed df onto hygro dataframe
    hygro_data.append(process_csv(csv_path))

combined = pd.concat(hygro_data, ignore_index=True)
# Need to join RH_pct and Temp_C into a single row based on datetime
