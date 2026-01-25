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
import numpy as np
from pathlib import Path
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

## --- INITIALIZE VARIABLES ---

# Define SOURCE data directory (where you read existing data FROM) ---
RAW_DATA_DIR = Path(os.path.join('..', '..', 'data', 'field_observations',
                                 'hygrochron', 'RAW'))

# Input (source data) filenames
SOURCE_FILE_PATTERN = "*.csv"

# Define OUTPUT data filename
OUT_DATA_DIR = os.path.join('..', '..', 'data', 'field_observations',
                                 'hygrochron')
HYGRO_DATA_FILENAME = OUT_DATA_DIR + '/hygrochron_2025_10min_per_well.csv'


# Final date time format for all files
#DATE_FORMAT_STRING = '%mm/%dd/%YYY %HH:%MM'

# Final columns
FINAL_COLUMNS = [
    'datetime', 
    'well_id', 
    'hygrochron_id',
    'RH_pct',
    'temperature_C',
    'source_file'
]

# EXPECTED_DTYPES = {
#     "datetime": "datetime64[ns]",
#     "well_id": "string",
#     "hygrochron_id": "string",
#     "RH_pct": "float64",
#     "Temperature_C": "float64",
#     "source_file": "string"
# }

## --- FUNCTIONS ---
# def enforce_schema(df):
#     for col, dtype in EXPECTED_DTYPES.items():
#         #df = df.replace({pd.NA: np.nan})
        
#         if col not in df:
#             df[col] = pd.Series([pd.NA] * len(df), dtype=dtype)
#         else:
#             df[col] = df[col].astype(dtype)
#     return df

def process_csv(csv_path) -> pd.DataFrame:
    """
    process csv from the iButton hygrochron using filename to identify
    the well_id; recording the datetime, relative humidity as percentage
    (RH_pct) and temperature (in C) following data model in FINAL_COLUMNS.

    Parameters: Path for source csv file
    
    Returns:
    (dataframe): single row with data from this single csv file, 
    """  
    
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
    # df["RH_pct"] = np.nan
    # df["temperature_C"] = np.nan
    #df["RH_pct"] = pd.Series(dtype="Float64")
    #df["temperature_C"] = pd.Series(dtype="Float64")

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

# Enforce data types in hygro_data list of dataframes
#       to prevent deprecation warning. 
#       Pandas doesn't like NA values for RH_pct or temp_C
#       but it works; efforts to address taking too much time.
#hygro_data = [enforce_schema(df) for df in hygro_data]  

# Concatenate all entries into a single dataframe
combined = pd.concat(hygro_data, ignore_index=True)

# 2. Join RH_pct and Temp_C into a single row based on datetime and well_id
joined = (
    combined
    .groupby(["datetime", "well_id"], as_index=False)
    .agg({
        "RH_pct": "first",
        "temperature_C": "first",
        "hygrochron_id": "first",
        "source_file": lambda x: ";".join(sorted(set(x)))
    })
)


# 3. Simple validation

# Ensure all files produced a dataframe
assert all(not df.empty for df in hygro_data), "DataFrame in hygro_data empty"   

# Ensure uniqueness
assert not joined.duplicated(["datetime", "well_id"]).any()

# Check missing pairings
missing = joined[joined[["RH_pct", "temperature_C"]].isna().any(axis=1)]

if not missing.empty:
    print(
        f"{len(missing)} rows are missing RH or temperature values"
    )

# 4. Save final "joined" dataframe as csv
joined.to_csv(HYGRO_DATA_FILENAME, index=False)
print("SUCCESS!! FILE SAVED TO: " + HYGRO_DATA_FILENAME)