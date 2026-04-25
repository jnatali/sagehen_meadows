
# ==============================================================================
# File:        well_utils.R
# Project:     sagehen_meadows
# Author:      Jennifer Natali
# Created:     2026-04-25
# Last updated:2026-04-25
#
# Description:
#   Utility functions for working with groundwater well IDs and associated
#   categorical metadata (meadow, plant functional type, hydrogeomorphic zone).
#
# Dependencies:
#   dplyr
#   stringr
#
# Usage:
#   source(file.path("scripts", "groundwater", "well_utils.R"))
#   or
#   source("scripts/groundwater/well_utils.R")
#   df <- get_well_categories(df)
#
# Notes:
#   - Assumes well_id encoding: [meadow][plant][zone][...]
#   - Unrecognized codes are preserved as-is.
#
# ============================================================================== 

## #' Parse well_id into categorical fields
#'
#' Extracts meadow, plant functional type (PFT), and hydrogeomorphic zone
#' from a well_id string and appends them as new columns to a data frame.
#'
#' @param df A data.frame or tibble containing a well ID column.
#' @param id_col Character. Name of the column containing well IDs.
#'
#' @details
#' The function assumes that `well_id` strings are structured such that:
#' - Character 1 = meadow code
#' - Character 2 = plant functional type (PFT)
#' - Character 3 = hydrogeomorphic zone (HGMZ)
#'
#' Codes are mapped as follows:
#'
#' Meadow:
#' - E = East
#' - K = Kiln
#' - L = Lower
#' - U = Upper
#'
#' Plant functional type:
#' - E = Sedge
#' - W = Willow
#' - H = Mixed Herbaceous
#' - F = Lodgepole Pine
#'
#' Hydrogeomorphic zone:
#' - R = Riparian
#' - T = Terrace
#' - F = Fan
#'
#' If a code is not recognized, the original code value is retained.
#'
#' @return
#' A data.frame (or tibble) with three additional columns:
#' - `meadow_id`
#' - `plant_type`
#' - `hydrogeo_zone`
#'
#' @examples
#' df <- data.frame(well_id = c("EWR01", "LHF02", "UTR03"))
#' df <- get_well_categories(df)
#'
#' @export
get_well_categories <- function(df, id_col = "well_id") {
  
  meadow_code <- stringr::str_sub(df[[id_col]], 1, 1)
  plant_code  <- stringr::str_sub(df[[id_col]], 2, 2)
  zone_code   <- stringr::str_sub(df[[id_col]], 3, 3)
  
  meadow_map <- c(
    "E" = "East",
    "K" = "Kiln",
    "L" = "Lower",
    "U" = "Upper"
  )
  
  zone_map <- c(
    "R" = "Riparian",
    "T" = "Terrace",
    "F" = "Fan"
  )
  
  plant_map <- c(
    "E" = "Sedge",
    "W" = "Willow",
    "H" = "Mixed Herbaceous",
    "F" = "Lodgepole Pine"
  )
  
  dplyr::mutate(
    df,
    meadow_id     = dplyr::coalesce(meadow_map[meadow_code], meadow_code),
    plant_type    = dplyr::coalesce(plant_map[plant_code], plant_code),
    hydrogeo_zone = dplyr::coalesce(zone_map[zone_code], zone_code)
  )
}