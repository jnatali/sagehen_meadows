
"""
##########  GROUNDWATER MARSS ANALYSIS SCRIPT  ##########  
Author: Jennifer Natali, jennifer.natali@berkeley.edu
Date Created: Sunday 17 November 2024

This script sets up and executes MARSS model for groundwater level data.

This code is under development and follows a functional programming paradigm.

Major Functions:
 

Requires  data files:
1. RAW groundwater data (in cm) for all years: 'groundwater_biweekly_RAW.csv'

TODOs documented in github repo issue tracking.

"""

# --- IMPORTS ---

# Load libraries
library(MARSS)

# --- INITIALIZE FILEPATH VARIABLES ---
# Setup directories and filepaths
home_dir='/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/'
repository_dir = paste(home_dir,'sagehen_meadows/', sep='')
groundwater_data_dir = 'data/field_observations/groundwater/biweekly_manual/'
groundwater_weekly_matrix_filepath = paste(repository_dir, groundwater_data_dir,
                                           'groundwater_weekly_matrix.csv',
                                           sep='')

# --- DEFINE FUNCTIONS ---

# LOAD AND VALIDATE RESPONSE DATA: Groundwater --------------------------------
# by: JNatali
# on: 17 Nov 2024
#
# TODO: filter out well/year grouping based on completeness
response_data <- load_response_data(){
  
  # Load response data: weekly groundwater measurements
  groundwater_data <- as.matrix(read.csv(groundwater_weekly_matrix_filepath),
                                header=TRUE)
  
  # Check matrix dimensions
  dim(groundwater_data)
  
  # Is it a 'matrix' object? check using the function 'class()'
  class(groundwater_data)
  
  return groundwater_data
}


# LOAD AND VALIDATE COVARIATE DATA: Discharge ---------------------------------
# by: JNatali
# on: 17 Nov 2024
# purpose: loads covariate data from files, validates it, apply z-score,
#          format as a matrix, and return z-scored data as matrix object

# TODO: Add covariate:
# --- Greenness values for vegetation plant functional types
#     (proxy for seasonality of photosynthesis rates)
#     (source: sub-daily images from tree-mounted, time-lapse camera)

# TODO: Consider Potential Hydro Covariates:
# --- Previous winter snowpack (how express?)
# --- Multi-year snowpack (know that groundwater at spring dated to be 30yo)
# --- Topographic Wetness Index
# --- Distance to Sagehen Creek or tributary stream channel, following topo

# TODO: Consider Potential Meteorological Covariates:
# --- Temperature (at east only vs near each site; consider daily mean, max, cumulative)
# --- Precip (total per day)
# --- Relative Humidity (consider daily mean)
# --- PAR (consider cumulative, daily mean, max)

# TODO: Consider how covariates correlate with each other??

covariate_matrix <- load_covariate_data(){
  
  ## -- GET DISCHARGE COVARIATE DATA from USGS --
  
  # Load NWIS data retrieval package for
  # USGS and EPA Hydro and Water Quality Data
  library(dataRetrieval)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  library(ISOweek)
  
  # Sagehen Creek NWIS site number and discharge code
  sagehen_NWIS_site <- "10343500"
  discharge_code <- "00060"
  
  sagehen_NWIS_data_available <- whatNWISdata(siteNumber=sagehen_NWIS_site,
                                              parameterCd=discharge_code,
                                              service="dv",
                                              statCd="00003")
  
  # get time range from groundwater time series data
  # (start and end date from week_year column labels)
  colnames(dat) <- sub("^X", "", colnames(dat))
  isoweek_range <- colnames(dat)[-1]
  isoweek_list <- as.list(isoweek_range)
  
  # get start date of the groundwater time series
  start_week <- isoweek_list[1]
  iso_start_year <- substr(start_week, 1, 4)
  iso_start_week <- substr(start_week, 5, 6)
  start_date <- ISOweek2date(paste0(iso_start_year, "-W", iso_start_week, "-1"))
  
  # get end date of the groundwater time series
  end_week <- isoweek_list[length(isoweek_list)]
  iso_end_year <- substr(end_week, 1, 4)
  # add one to isoweek so I capture the last date of the time series
  # (not the first day of the last week)
  iso_end_week <- as.integer(substr(end_week, 5, 6)) + 1
  iso_end_week <- sprintf("%02d", iso_end_week)
  end_date <- ISOweek2date(paste0(iso_end_year, "-W", iso_end_week, "-1"))
  
  # get the mean daily discharge for the appropriate date range
  # reported in cfs according to USGS
  discharge <- readNWISdv(sagehen_NWIS_site, 
                          discharge_code, start_date, end_date)
  # limit to two columns: date and flow
  discharge <- discharge[, 3:4] %>%
    rename(date = Date, flow_cfs = X_00060_00003)
  
  # add new column with year and isoweek combined
  # (e.g. 201820 for year 2018, week 20)
  discharge <- discharge %>%
    mutate(year_week = as.character(paste0(year(as.Date(date)), 
                                           sprintf("%02d", isoweek(date)))))
  
  # average flow (7 days) for each year_week
  # --- TODO: is averaging the best representation of the data?
  discharge <- discharge %>%
    group_by(year_week) %>%
    summarise(
      flow_cfs = mean(flow_cfs, na.rm = TRUE),
      .groups = "drop"
    )
  
  # create grid to match groundwater time series
  discharge_grid <- expand_grid(
    year_week = as.character(isoweek_list)
  )
  
  # join the grid with discharge data
  discharge_grid <- discharge_grid %>%
    left_join(discharge, by = "year_week")
  
  # transform to timesteps as columns
  discharge_matrix <- discharge_grid %>%
    pivot_wider(
      names_from = year_week,
      values_from = flow_cfs
    )
  
  # check completeness
  discharge_matrix %>%
    summarize(
      na_sum = sum(across(everything(), ~ is.na(.))),
      na_percent = 100 * na_sum / (n() * ncol(.))
    )
  
  # Convert to matrix, validate and check dimensions
  discharge_matrix <- as.matrix(discharge_matrix)
  class(discharge_matrix)
  dim(discharge_matrix)
  
  # Z-score flow values
  discharge_covariate <- zscore(discharge_matrix)
}

# BUILD Z MATRICES ------------------------------------------------------------
# by: JNatali
# on: 17 Nov 2024
# purpose: sets up Z matrices for the model runs, 
#          returns them as a list of matrices

# TODO: Consider other Z matrices:
#           SITE x PFT x HGMZ combo
#           well distance from Sagehen Creek (well across a transect)

# TODO: Use dynamic factor analysis to improve categorization of HGMZ / PFT
#       address uncertainty about categorization; see MARSS User Guide Ch 10.

z_matrix_list <- get_Z_matrices() {

  # H1: Every well is its own state; Z is the identity matrix
  Z_1 = "identity"
  
  ## MEADOW SITES ##
  # H2: 3 meadow sites (Kiln, East, Lo); each is its own state, an independent dimension
  Z_2 = matrix(NA, nrow=0, ncol=3)
  # --- loop thru well_ids to determine meadow site
  for (i in 1:nrow(dat)) {
    well_id <- dat[i,1]
    meadow <- substring(well_id, 1, 1)
    #print(meadow)
    if (meadow == "E") {
      row <- c(1, 0, 0)
    } else if (meadow == "K") {
      row <- c(0, 1, 0)
    } else if (meadow == "L") {
      row <- c(0, 0, 1)
    } else print("WARNING: Well Meadow Site is NOT E, K, or L")
    Z_2 <- rbind(Z_2, row)
  }
  dim(Z_2)
  
  ## PLANT FUNCTIONAL TYPES ##
  # H3: PFT x 4 (sedge, willow, mixed herbaceous, pine)
  Z_3 = matrix(NA, nrow=0, ncol=4)
  # --- loop thru well_ids to determine PFT
  for (i in 1:nrow(dat)) {
    well_id <- dat[i,1]
    pft <- substring(well_id, 2, 2)
    #print(pft)
    if (pft == "E") {
      row <- c(1, 0, 0, 0)
    } else if (pft == "W") {
      row <- c(0, 1, 0, 0)
    } else if (pft == "H") {
      row <- c(0, 0, 1, 0)
    } else if (pft == "F") {
      row <- c(0, 0, 0, 1)
    } else print("WARNING: Well PFT is NOT E, W, H or F")
    Z_3 <- rbind(Z_3, row)
  }
  dim(Z_3)
  
  ## HYDROGEOMORPHIC ZONES ##
  # H4: HGMZ x 3 (riparian, terrace, fan)
  Z_4 = matrix(NA, nrow=0, ncol=3)
  # --- loop thru well_ids to determine PFT
  for (i in 1:nrow(dat)) {
    well_id <- dat[i,1]
    hgmz <- substring(well_id, 3, 3)
    #print(hgmz)
    if (hgmz == "R") {
      row <- c(1, 0, 0)
    } else if (hgmz == "T") {
      row <- c(0, 1, 0)
    } else if (hgmz == "F") {
      row <- c(0, 0, 1)
    } else print("WARNING: Well HGMZ is NOT R, T, or F")
    Z_4 <- rbind(Z_4, row)
  }
  dim(Z_4)
  
  ## STRATIFIED COMBO ##
  # H5: PFT x HGMZ (3x4 = 12 combos)
  Z_5 = matrix(0, nrow=dim(dat)[1], ncol=12)
  colnames(Z_5) <- c("ER", "ET", "EF", "WR", "WT", "WF", "HR", "HT", "HF", "FR", "FT", "FF")
  # --- loop thru well_ids to determine PFT x HGMZ
  for (i in 1:nrow(dat)) {
    well_id <- dat[i,1]
    combo <- substring(well_id, 2, 3)
    # Find the column that matches the PFT x HGMZ combo characters
    col_index <- which(colnames(Z_5) == combo)
    if (length(col_index) == 1) { # if combo is valid
      Z_5[i, col_index] <- 1 # assign to 1
    }
  }
  dim(Z_5)
  
  ## CREATE LIST OF MATRICES AND RETURN
  Z_matrix_list <- list(Z_1, Z_2, Z_3, Z_4, Z_5)
  return(Z_matrix_list)
  
}

# SPECIFY MAR/MARSS PARAMETERS ------------------------------------------------
# by: JNatali
# on: 17 Nov 2024
# purpose: read params from a csv or xls file for a set of models



# RUN THE MODEL: FIT AND BOOTSTRAP --------------------------------------------
# by: JNatali
# on: 17 Nov 2024
# purpose: run models, generate and save results

# ASSESS THE MODELS -----------------------------------------------------------
# by: JNatali
# on: 17 Nov 2024
# purpose: plot and compare model results, evaluate hypotheses
