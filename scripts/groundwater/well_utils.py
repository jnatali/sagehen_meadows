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
    Checks the name of the FIELD well_ids,
    NOT the renamed, recategorized well ids used in analysis.
    """
    valid_ids = load_valid_well_ids(VALID_WELL_ID_PATH)
    
    invalid = set(df[id_col].unique()) - valid_ids
    if invalid:
        raise ValueError(
            f"Invalid well_id(s) found: {sorted(invalid)}"
        )

## Renaming / Correction
def correct_well_ids(df) -> pd.DataFrame:
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
    validate_well_ids(df, id_col=id_col)
    df = correct_well_ids(df)
    df = get_well_categories(df)

    return df

