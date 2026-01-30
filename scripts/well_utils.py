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

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

VALID_WELL_ID_PATH = RAW_DIR / "Wells_Unique_Id.txt"
CORRECTIONS_PATH = META_DIR / "well_id_corrections.csv"

# --- FUNCTIONS ---

## I/O Helpers
def load_valid_well_ids(path):
    """
    Load list of valid, physical well IDs.
    """
    path = Path(path)
    return set(path.read_text().splitlines())


def load_well_id_corrections(path):
    """
    Load correction table with columns:
    original_well_id, analysis_well_id
    """
    return pd.read_csv(path)


## Validation
def validate_well_ids(df, id_col, valid_ids):
    """
    Assert that all well IDs in df[id_col] are in valid_ids.
    """
    invalid = set(df[id_col].unique()) - valid_ids
    if invalid:
        raise ValueError(
            f"Invalid well_id(s) found: {sorted(invalid)}"
        )

## Renaming / Correction
def apply_well_id_corrections(
    df,
    corrections_df,
    id_col="well_id",
    new_col="analysis_well_id",
):
    """
    Add a corrected well ID column using a lookup table.
    Original ID is preserved.
    """
    corrections = (
        corrections_df
        .set_index("original_well_id")["analysis_well_id"]
    )

    df = df.copy()
    df[new_col] = df[id_col].map(corrections).fillna(df[id_col])

    return df

## Categorization of site, HGMZ, and PFT
def get_well_categories(
    df,
    id_col="analysis_well_id",
):
    """
    Parse meadow, hydrogeomorphic zone, and PFT
    from a well ID string.
    """
    df = df.copy()

    df["meadow_id"] = df[id_col].str[0]
    df["hydrogeomorphic_zone"] = df[id_col].str[1]
    df["plant_functional_type"] = df[id_col].str[2]

    return df


