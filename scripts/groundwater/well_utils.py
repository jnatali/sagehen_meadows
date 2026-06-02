#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 09:34:25 2026
#########  WELL UTILITY SCRIPT  ##########  

This module provides functions to manage groundwater well data, 
especially well_id and well characteristcs, for scripts used 
throughout the project.


@author: jnat
"""

# --- DUNDERS ---
__author__ = 'Jennifer Natali'
__copyright__ = 'Copyright (C) 2026 Jennifer Natali'
__license__ = 'NOT Licensed, Private Code under Development, DO NOT DISTRIBUTE'
__maintainer__ = 'Jennifer Natali'
__email__ = 'jennifer.natali@berkeley.edu'
__status__ = 'Development'

# --- IMPORTS ---
## Basic libraries
import pandas as pd
from pathlib import Path
import warnings

# --- GLOBAL VARIABLES ---

## -- INITIALIZE FILE VARIABLES --

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
GW_DIR = DATA_DIR / "field_observations/groundwater"

VALID_WELL_ID_PATH = GW_DIR / "well_unique_id.txt"
CORRECTIONS_PATH = GW_DIR / "well_renamed_id.csv"

# --- FUNCTIONS ---

## I/O Helpers
def load_valid_well_ids(path):
    """
    Load list of valid, physical well IDs.
    """
    return set(path.read_text().splitlines())


def load_well_id_corrections(path):
    """
    Load correction table with columns:
    original_well_id, analysis_well_id
    """
    return pd.read_csv(path)


## Validation
def validate_well_ids(df, id_col):
    """
    Assert that all well IDs in df[id_col] are in valid_ids.
    Checks the name of  well_ids (not field ids) if id_col = "well_id"
    so best if called after apply_well_id_corrections
    
    - Removes rows with missing well_id and no other populated fields.
    - Warns about rows with missing well_id but other populated fields.
    - Warns about invalid well IDs.
    """
    
    
    df = df.copy()
    
    # Handle missing well_ids
    missing_mask = df[id_col].isna()

    if missing_mask.any():
    
        rows_to_drop = []
    
        for idx, row in df.loc[missing_mask].iterrows():
    
            # Ignore the well_id column itself
            other_fields = row.drop(labels=[id_col])
    
            # Treat NaN, None, and empty strings as missing
            populated = other_fields[
                other_fields.notna()
                & (other_fields.astype(str).str.strip() != "")
            ]
    
            if len(populated) == 0:
                rows_to_drop.append(idx)
            else:
                warnings.warn(
                    f"\n\nMISSING {id_col} in ROW {idx} contains data: "
                    f"{populated.to_dict()}\n\n",
                    UserWarning,
                    stacklevel=2,
                )
    
        if rows_to_drop:
            df = df.drop(index=rows_to_drop)
    
    # Validate non-missing well_ids
    valid_ids = load_valid_well_ids(VALID_WELL_ID_PATH)
    
    invalid = set(df[id_col].unique()) - valid_ids
    
    if invalid:
        warnings.warn(
            f"\n\nINVALID well_ids FOUND!: {(invalid)}\n\n",
            UserWarning,
            stacklevel=2)
        # raise ValueError(
        #     f"Invalid well_id(s) found: {(invalid)}"
        # )

## Renaming / Correction
def apply_well_id_corrections(
    df
):
    """
    Add a corrected well ID column using a lookup table.
    Original ID is preserved as field_well_id
    """
    
    # get corrections datafram from load_well_id_corrections(path)
    corrections_df = load_well_id_corrections(CORRECTIONS_PATH)
    
    # map corrections
    corrections = (
        corrections_df
        .set_index("well_field_id")["well_id"]
    )

    # return new data frame with orginal id and new id
    df = df.copy()
    df["field_well_id"] = df["well_id"] 
    df["well_id"] = df["well_id"].map(corrections).fillna(df["well_id"])

    return df

## Categorization of site, HGMZ, and PFT
def get_well_categories(
    df,
    id_col="well_id",
):
    """
    Parse meadow, hydrogeomorphic zone, and PFT
    from a well_id string.
    """
    df = df.copy()

    meadow_code = df[id_col].str[0]
    plant_code = df[id_col].str[1]
    zone_code = df[id_col].str[2]
    
    meadow_map = {
    "E": "East",
    "K": "Kiln",
    "L": "Lower",
    "U": "Upper",
    }

    zone_map = {
    "R": "Riparian",
    "T": "Terrace",
    "F": "Fan",
    }

    plant_map = {
    "E": "Sedge",
    "W": "Willow",
    "H": "Mixed Herbaceous",
    "F": "Lodgepole Pine",
    }
   
    df["meadow_id"] = meadow_code.map(meadow_map).fillna(meadow_code)
    df["plant_type"] = plant_code.map(plant_map).fillna(plant_code)
    df["hydrogeo_zone"] = zone_code.map(zone_map).fillna(zone_code)

    return df

def process_well_ids(
    df,
    id_col="well_id",
):
    """
    End-to-end well ID processing:
      1. validate physical IDs
      2. apply corrections
      3. assign categories
    """
    df = apply_well_id_corrections(df)
    validate_well_ids(df, id_col=id_col)
    df = get_well_categories(df)

    return df

