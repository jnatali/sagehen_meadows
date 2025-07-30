##########  GROUNDWATER MARSS ANALYSIS SCRIPT  ##########  
# Author: Jennifer Natali, jennifer.natali@berkeley.edu
# Date Created: Sunday 17 November 2024
# 
# This script sets up and executes MARSS model(s) for weekly groundwater data.
# 
# This version supports:
# - a 'timespan' parameter that can be:
#         'continuous' where weekly observations continue from one year to next
#         'each year' where only one year of observations is represented and run
#         'stacked' one yr of observations per well, but well_id includes yr
# - a 'Z' parameter which can be:
#         'identity' as accepted by MARSS
#         'grouped' which creates a list of Z matrices to test specific
#                     hypotheses; depends on value of 'timespan'
# 
# This code is under development and follows a procedural programming paradigm.
# 
# Requires  data files:
# 1. RAW groundwater data (in cm) for all years: 'groundwater_biweekly_RAW.csv'
# 2. A model parameterization file: 'MARSS_groundwater_parameters.csv'
# 
# TODOs documented in github repo issue tracking.

# ------ IMPORTS ------

# Load libraries
library(MARSS)
library(lubridate)
library(dplyr)
library(tidyr)


# ------ INITIALIZE GLOBAL VARIABLES ------
#### Info about the data
# TODO: set as model param
year_range <- c(2018,2019,2021,2024)
# seemed to be working with 2021 + 2024 only
#year_range <- c(2018, 2019, 2021, 2024)
#year_range <- c(2018)

# time limit for filtering groundwater observations
time_limit <- 12 # only include gw well measurements prior to this time (i.e. noon)

# completeness limit for % of entries NA values per row
completeness_limit <- 0.88 # default, can be overridden by model params
# NOTE: at 0.85 13 wells removed, 0.8800->8 wells, 0.90->5 wells, at 0.95->2

# default max iterations
number_iterations <- 10000

# flag (binary) to keep or trim the first two weeks
# TODO: update code to trim first/last NA columns of the series
# TODO: set as model param
trim_first_two_weeks = FALSE

# flag (binary) to fill gaps for entire year (vs. between weeks during summer)
# TODO: set as model param
fill_full_year_gaps = FALSE

# today's date for running models from model parameter file listed for today
today <- Sys.Date()
formatted_date <- format(today, "%Y_%m%d")

# initialize a Z_grouping_id_list global variable
# for assigning a relevant model_id with grouped Z matrix
Z_grouping_id_list <- NULL

# Setup directories and filepaths
home_dir='/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/'
repository_name = 'sagehen_meadows'
repository_dir = paste(home_dir, repository_name, '/', sep='')

groundwater_matrix_filename = 'groundwater_weekly_matrix.csv'
groundwater_data_dir = 'data/field_observations/groundwater/biweekly_manual/'
marss_script_dir = 'scripts/groundwater/MARSS/'
marss_results_dir = paste(home_dir, repository_name, '/results/MARSS/', sep='')

groundwater_rawdata_filepath = paste(repository_dir, groundwater_data_dir,
                                     'groundwater_daily_FULL_COMBINED.csv',
                                     sep='')
groundwater_weekly_matrix_filepath = paste(repository_dir, groundwater_data_dir,
                                           groundwater_matrix_filename,
                                           sep='')
model_parameter_filepath = paste(repository_dir, marss_script_dir,
                                 'MARSS_groundwater_parameters.csv',
                                 sep='')

# ------ DEFINE FUNCTIONS ------

#### PREPARE GROUNDWATER DATA
# by: JNatali
# on: 18 Nov 2024
# purpose: opens biweekly groundwater data 
#          (manually measured then transformed relative to ground), 
#          manipulates into matrix form, saves it.
# returns: groundwater_weekly_matrix, evenly-spaced weekly matrix of groundwater
#          well readings for all years.
#          
# ---TODO: Add "greater_than" data to increase completeness (for now)
# ---TODO: Consider adding data from Kirchner 2006-2008 B+D xect
# ---TODO: Get data from other (not my) transducers for 2018-2024?
# ---TODO: summary and analysis of data in MARSS_Sagehen_Groundwater.Rmd
prepare_groundwater_data <- function(){
  
  # Load groundwater data
  groundwater <- read.csv(groundwater_rawdata_filepath)

  # Manage dates and times
  groundwater$timestamp <- ymd_hms(groundwater$timestamp)
  # Create columns for date and isoweek (starts on Monday)
  groundwater <- groundwater %>% mutate(
    date = as.Date(timestamp), 
    year = year(timestamp),
    isoweek = isoweek(date),
    day_of_year = yday(date))
  
  # summarize the full times series
  summary(groundwater)
  nrow_groundwater_orig <- nrow(groundwater)
  
  ## ORGANIZE BY AN EVEN TIMESTEP
  # filter measurements, only before threshold time
  groundwater <- groundwater %>%
    filter(hour(timestamp) <= time_limit) # time_limit defined in global vars
  
  # get ranges of isoweeks (min to max) depending on flag (global variable)
  if (fill_full_year_gaps == FALSE) {
    isoweek_range <- min(groundwater$isoweek):max(groundwater$isoweek)
  } else {
    isoweek_range <- 1:52
  }
  
  # setup column names, e.g. 202401 where the last two digits are the isoweek
  year_week_range <- as.character(unlist(lapply(year_range, function(year) {
    paste0(year, sprintf("%02d", isoweek_range))
  })))
  
  # add new column with year and isoweek combined
  # (e.g. 201820 for year 2018, week 20)
  groundwater <- groundwater %>%
    mutate(year_week = as.character(paste0(year, sprintf("%02d", isoweek))))
  
  # if multiple entries per well_id and year_week, average them
  # --- TODO: is averaging the best representation of the data?
  groundwater <- groundwater %>%
    group_by(well_id, year_week) %>%
    summarise(
      ground_to_water_cm = mean(ground_to_water_cm, na.rm = TRUE),
      .groups = "drop"
    )

  # create a complete grid of all well_id and year_week values
  groundwater_full_grid <- expand_grid(
    well_id = unique(groundwater$well_id),
    year_week = year_week_range
  )
  
  # join the complete grid with groundwater
  groundwater_full_grid <- groundwater_full_grid %>%
    left_join(groundwater, by = c("well_id", "year_week"))
  
  # check for duplicates
  duplicate_groundwater <- groundwater_full_grid %>%
    group_by(well_id, year_week) %>%
    summarize(
      count = n(),
      .groups = "drop"
    ) %>%
    filter(count>1)
  
  # create new dataframe with timesteps as columns and one unique well_id per row
  groundwater_weekly_matrix <- groundwater_full_grid %>%
    pivot_wider(
      names_from = year_week,
      values_from = ground_to_water_cm,
      values_fill = NA
    )

  # remove first two weeks (first two columns) if flagged at top of file
  if (trim_first_two_weeks) { 
    groundwater_weekly_matrix <- groundwater_weekly_matrix[, -c(2,3)]
  }
  #print(names(groundwater_weekly_matrix[1]))
  
  write.csv(groundwater_weekly_matrix, groundwater_weekly_matrix_filepath, 
            row.names = FALSE)
  return(groundwater_weekly_matrix)
}

#### STACK GROUNDWATER DATA
# by: JNatali
# on: 24 Nov 2024
# purpose: transforms the evenly-spaced groundwater_weekly_matrix 
#          so it's stacked by year 
#          with rows uniquely identified by well_id + year
#          and columns ordered by isoweeks.
# returns: groundwater_weekly_stacked_matrix, evenly-spaced weekly matrix of 
#          groundwater measurements by well_id + year
#          
stack_groundwater_data <- function(groundwater_data){
  
  # RESTRUCTURE the groundwater dataframe
  # restructure df to long format and extract year, week from YYYYww columns
  groundwater_stack <- as.data.frame(groundwater_data) %>%
    pivot_longer(cols = -well_id,
                 names_to = 'yearweek',
                 values_to = 'value') %>%
    mutate(
      year = substr(yearweek, 1, 4),
      week = substr(yearweek, 5, 6)
    ) %>%
    select(-yearweek)
  
  # rename identifying column
  groundwater_stack <- groundwater_stack %>%
    mutate(
      well_id = paste(well_id, year, sep='-')
    ) %>%
    select(-year)

  # restructure to wide format with one row per well_id + year
  groundwater_stack_matrix <- groundwater_stack %>%
    pivot_wider(
      names_from = week,
      values_from = value
    )
  
  ## REMOVE the first sequential NA columns
  # identify all NA columns, exclude 'well_id' first column
  na_cols <- sapply(groundwater_stack_matrix[, -1], function(col) all(is.na(col)))
  # get index of first and last non-NA column
  first_non_na <- which(!na_cols)[[1]]
  # remove initial sequential columns, if any
  if (!is.na(first_non_na)) {
    groundwater_stack_matrix <- groundwater_stack_matrix[, c(1, (first_non_na+1):ncol(groundwater_stack_matrix))]
  } 
  na_cols <- sapply(groundwater_stack_matrix[, -1], function(col) all(is.na(col)))
  last_non_na <- max(which(!na_cols))
  # only keep columns to last_non_na  
  groundwater_stack_matrix <- groundwater_stack_matrix[, 1:(last_non_na-1)]
  return(groundwater_stack_matrix)
}

#### FILTER INCOMPLETE WELLS
filter_incomplete_wells <- function(groundwater_matrix, limit){
  
  if (missing(limit)) limit <- completeness_limit
  # NOTE: completeness_limit defined as global variable at top of file
  
  # ensure groundwater_matrix is a dataframe
  groundwater_df <- as.data.frame(groundwater_matrix)
  
  # filter out relatively incomplete wells (across the entire multi-yr series)
  total_rows <- nrow(groundwater_df)
  total_columns <- ncol(groundwater_df)
  # calculate % of NA values per row
  na_sums <- rowSums(is.na(groundwater_df))
  na_percent <- rowSums(is.na(groundwater_df)) / total_columns
  # remove rows based on completeness relative to pre-defined limit
  new_groundwater_df <- groundwater_df[na_percent <= limit, ]
  
  # print removal alert
  print(paste0('ALERT: # of rows removed after completeness check: ',
               total_rows - nrow(new_groundwater_df)))
  removed_wells <- setdiff(groundwater_df$well_id, 
                           new_groundwater_df$well_id)
  print('removed wells')
  print(removed_wells)
  
  return(as.matrix(new_groundwater_df))
}

#### LOAD AND VALIDATE RESPONSE DATA
# by: JNatali
# on: 17 Nov 2024
# returns: response_data, a dataframe
# 
load_response_data <- function(weekly_matrix) {
  
  # if no params pass, load response data: weekly groundwater measurements
  if (missing(weekly_matrix)) { 
      weekly_matrix <- read.csv(groundwater_weekly_matrix_filepath,
                                  header=TRUE, check.names=FALSE)
      }
  
  # Remove any "X" prefix, if it's present
  colnames(weekly_matrix) <- gsub("^X","",colnames(weekly_matrix))
  
  # Convert to a matrix
  weekly_matrix <- as.matrix(weekly_matrix)
  
  # Check matrix dimensions
  dim(weekly_matrix)
  
  # Is it a 'matrix' object? check using the function 'class()'
  class(weekly_matrix)
  
  return(weekly_matrix)
}

#### LOAD COVARIATE DATA
# by: JNatali
# on: 17 Nov 2024
# purpose: loads covariate data from files, validates it, apply z-score,
#          format as a matrix, and return z-scored data as matrix object
# returns: covariate_matrix

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

load_covariate_data <- function() {
  
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
  return(discharge_covariate)
}

#### BUILD Z MATRICES
# by: JNatali
# on: 17 Nov 2024
# purpose: sets up Z matrices for the model runs, 
#          returns them as a list of matrices;
#          does NOT setup a year-based Z matrix
# returns: z_matrix_list, a list of matrices
#
# TODO: Refactor so that only one get_z_matrices function

get_z_matrices_no_years <- function(gw_data) {
  
  ## MEADOW SITES ##
  # 3 meadow sites (Kiln, East, Lo); each is its own state, an independent dimension
  Z_site = matrix(NA, nrow=0, ncol=3)
  # --- loop thru well_ids to determine meadow site
  for (i in 1:nrow(gw_data)) {
    well_id <- gw_data[i,1]
    meadow <- substring(well_id, 1, 1)
    #print(meadow)
    if (meadow == "E") {
      row <- c(1, 0, 0)
    } else if (meadow == "K") {
      row <- c(0, 1, 0)
    } else if (meadow == "L") {
      row <- c(0, 0, 1)
    } else print("WARNING: Well Meadow Site is NOT E, K, or L")
    Z_site <- rbind(Z_site, row)
  }
  rownames(Z_site) <- NULL
  colnames(Z_site) <- NULL
  dim(Z_site)
  
  ## PLANT FUNCTIONAL TYPES ##
  # PFT x 4 (sedge, willow, mixed herbaceous, pine)
  Z_pft = matrix(NA, nrow=0, ncol=4)
  # --- loop thru well_ids to determine PFT
  for (i in 1:nrow(gw_data)) {
    well_id <- gw_data[i,1]
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
    Z_pft <- rbind(Z_pft, row)
  }
  rownames(Z_pft) <- NULL
  colnames(Z_pft) <- NULL
  dim(Z_pft)
  
  ## HYDROGEOMORPHIC ZONES ##
  # HGMZ x 3 (riparian, terrace, fan)
  Z_hgmz = matrix(NA, nrow=0, ncol=3)
  # --- loop thru well_ids to determine PFT
  for (i in 1:nrow(gw_data)) {
    well_id <- gw_data[i,1]
    hgmz <- substring(well_id, 3, 3)
    #print(hgmz)
    if (hgmz == "R") {
      row <- c(1, 0, 0)
    } else if (hgmz == "T") {
      row <- c(0, 1, 0)
    } else if (hgmz == "F") {
      row <- c(0, 0, 1)
    } else print("WARNING: Well HGMZ is NOT R, T, or F")
    Z_hgmz <- rbind(Z_hgmz, row)
  }
  rownames(Z_hgmz) <- NULL
  colnames(Z_hgmz) <- NULL
  dim(Z_hgmz)
  
  ## STRATIFIED COMBO ##
  # PFT x HGMZ (3x4 = 12 combos)
  Z_pftXhgmz = matrix(0, nrow=dim(gw_data)[1], ncol=12)
  colnames(Z_pftXhgmz) <- c("ER", "ET", "EF", "WR", "WT", "WF", "HR", "HT", "HF", "FR", "FT", "FF")
  # --- loop thru well_ids to determine PFT x HGMZ
  for (i in 1:nrow(gw_data)) {
    well_id <- gw_data[i,1]
    combo <- substring(well_id, 2, 3)
    # Find the column that matches the PFT x HGMZ combo characters
    col_index <- which(colnames(Z_pftXhgmz) == combo)
    if (length(col_index) == 1) { # if combo is valid
      Z_pftXhgmz[i, col_index] <- 1 # assign to 1
    }
  }
  dim(Z_pftXhgmz)
  
  # Set z_grouping_id_list
  Z_grouping_id_list <<- c('site', 'pft', 'hgmz', 'pftXhgmz')
  
  ## CREATE LIST OF MATRICES AND RETURN
  Z_matrix_list <- list(Z_site, Z_pft, Z_hgmz, Z_pftXhgmz)
  return(Z_matrix_list)
  
}

#### BUILD Z MATRICES
# by: JNatali
# on: 25 Nov 2024 (after the previous function)
# purpose: sets up Z matrices for the model runs, 
#          returns them as a list of matrices
#          with consideration of the year as part of the well name, e.g. -2018
# returns: z_matrix_list, a list of matrices

# TODO: Refactor so that only one get_z_matrices function
# 
# TODO: Consider other Z matrices:
#           SITE x PFT x HGMZ combo
#           well distance from Sagehen Creek (well across a transect)

# TODO: Use dynamic factor analysis to improve categorization of HGMZ / PFT
#       address uncertainty about categorization; see MARSS User Guide Ch 10.

get_z_matrices <- function(gw_data) {

  # --- loop thru well_ids to determine sub-categories
  gw_names <- as.data.frame(gw_data) %>%
    mutate (
      well = sub("-\\d{4}$", "", well_id), # pattern match, exclude year at end
      meadow = substring(well_id, 1, 1), #JN 01/07/2025 changed variable name from meadows to meadow
      pft = substring(well_id, 2, 2),
      hgmz = substring(well_id, 3, 3),
      year = sub(".*-(.*)-(\\d{4})$", "\\2", well_id) # 4 chars after 2nd dash
    )
  
  wells <- unique(gw_names$well) 
  meadows <- unique(gw_names$meadow)
  pfts <- unique(gw_names$pft)
  hgmzs <- unique(gw_names$hgmz)
  years <- unique(gw_names$year) #TODO: why is this only 2024?
  
  ## PANMICTIC ##
  # All wells treated the same, grouped by year only
  column_names <- years # a character
  Z_pan <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  colnames(Z_pan) <- column_names 
  
  for (i in 1:nrow(gw_names)) {
    Z_pan[i, gw_names$year[i]] <- 1
  }
  colnames(Z_pan) <- NULL
  
  # # TODO: Get Z='identity' working; for now it's throwing a MARSSinits error
  # ## IDENTITY ##
  # # Identity for each year
  # 
  # # create a grid dataframe of all possible combos of well+year
  # site_combos <- expand.grid(well = wells, year = years)
  # column_names <- paste(site_combos$well, site_combos$year, sep = "+")
  # Z_identity <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  # colnames(Z_identity) <- column_names
  # 
  # for (i in 1:nrow(gw_names)) {
  #   well_year_combo <- paste(gw_names$well[i], gw_names$year[i], sep = "+")
  #   Z_identity[i, well_year_combo] <- 1
  # }
  # colnames(Z_identity) <- NULL
  
  ## MEADOW SITES ##
  # 3 meadow sites (Kiln, East, Lo); each is its own state

  # create a grid dataframe of all possible combos of meadow+year
  site_combos <- expand.grid(meadow = meadows, year = years)
    
  column_names <- paste(site_combos$meadow, site_combos$year, sep = "+")
  Z_site <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  colnames(Z_site) <- column_names
  
  for (i in 1:nrow(gw_names)) {
    meadow_year_combo <- paste(gw_names$meadow[i], gw_names$year[i], sep = "+")
    Z_site[i, meadow_year_combo] <- 1
  }
  colnames(Z_site) <- NULL
  
  ## PLANT FUNCTIONAL TYPES ##
  # PFT x 4 (sedge, willow, mixed herbaceous, pine)
  
  # create a grid dataframe of all possible combos of pft+year
  site_combos <- expand.grid(pft = pfts, year = years)
  
  column_names <- paste(site_combos$pft, site_combos$year, sep = "+")
  Z_pft <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  colnames(Z_pft) <- column_names
  
  for (i in 1:nrow(gw_names)) {
    pft_year_combo <- paste(gw_names$pft[i], gw_names$year[i], sep = "+")
    Z_pft[i, pft_year_combo] <- 1
  }
  colnames(Z_pft) <- NULL
  
  
  ## HYDROGEOMORPHIC ZONES ##
  # HGMZ x 3 (riparian, terrace, fan)
  
  # create a grid dataframe of all possible combos of hgmz+year
  site_combos <- expand.grid(hgmz = hgmzs, year = years)
  
  column_names <- paste(site_combos$hgmz, site_combos$year, sep = "+")
  Z_hgmz <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  colnames(Z_hgmz) <- column_names
  
  for (i in 1:nrow(gw_names)) {
    hgmz_year_combo <- paste(gw_names$hgmz[i], gw_names$year[i], sep = "+")
    Z_hgmz[i, hgmz_year_combo] <- 1
  }
  colnames(Z_hgmz) <- NULL
  
  
  ## STRATIFIED COMBO ##
  # PFT x HGMZ (3x4 = 12 combos)
  
  site_combos <- expand.grid(pft = pfts, hgmz = hgmzs, year = years)
  column_names <- paste(site_combos$pft, site_combos$hgmz, site_combos$year, sep = "+")
  Z_pftXhgmz <- matrix(0, nrow = nrow(gw_names), ncol = length(column_names))
  colnames(Z_pftXhgmz) <- column_names
  
  # Fill the matrix with 1s based on pft, hgmz, and year from gw_names
  for (i in 1:nrow(gw_names)) {
    # Get the pft, hgmz, and year for the current row
    pft_year_hgmz_combination <- paste(gw_names$pft[i], 
                                       gw_names$hgmz[i], 
                                       gw_names$year[i], 
                                       sep = "+")
    
    # Set the corresponding cell in the matrix to 1
    Z_pftXhgmz[i, pft_year_hgmz_combination] <- 1
  }
  colnames(Z_pftXhgmz) <- NULL
  
  # Set z_grouping_id_list
  # Z_grouping_id_list <<- c('pan','identity','site', 'pft', 'hgmz', 'pftXhgmz')
  Z_grouping_id_list <<- c('pan','site', 'pft', 'hgmz', 'pftXhgmz')
  
  ### CREATE LIST OF MATRICES AND RETURN
  #Z_matrix_list <- list(Z_pan, Z_identity, Z_site, Z_pft, Z_hgmz, Z_pftXhgmz)
  Z_matrix_list <- list(Z_pan, Z_site, Z_pft, Z_hgmz, Z_pftXhgmz)
  
  return(Z_matrix_list)
}

#### SPECIFY MARSS PARAMS
# by: JNatali
# on: 17 Nov 2024
# purpose: read params from a csv or xls file for a set of models
#          will only read models to run for today's date (runtime)
# returns: param_dataframe
get_model_parameters <- function(start_number, end_number) {
  
  # read parameter file as a dataframe, format data using lubridate
  params <- read.csv(model_parameter_filepath)
  params$run_date <- mdy(params$run_date)
  
  # filter params to run models for today
  filter_date <- today
  
  # check if start and stop IDs are missing or present, then filter
  if (!missing(start_number) && !missing(stop_number)){
    # filter for today and specified model #s
    params <- params %>%
      filter(run_date == filter_date, ID >= start_number, ID <= stop_number)
  } else {
    # filter by date only
    params <- params %>%
      filter(run_date == filter_date)
  }
  
  if (nrow(params) < 1) print("ALERT! No parameters")
  
  return(params)
}

#### PROCESS MODEL RESULTS
# by: JNatali
# on: 20 Nov 2024
# purpose: reformat the model run summaries prior to saving
# returns: merged_results dataframe with reformatted structure
process_model_results <- function(model_result_dataframe,
                                  model_param_dataframe,
                                  model_ID, number_obs){
  
  # ASSIGN model ID and date to the result dataframe
  new_result_row <- data.frame(
    ID = model_ID,
    run_date = model_param_dataframe$run_date,
    observations = number_obs,
    completeness = model_param_dataframe$completeness,
    stringsAsFactors = FALSE)
  
  # Merge with "glance" summary from model run
  merged_results <- merge(new_result_row, 
                          model_result_dataframe, # "glance" dataframe + run_minutes
                          by = NULL)
  # reorder columns
  merged_results <- merged_results[, c("ID", "run_date", "run_minutes", 
                                       "observations", "completeness", 
                                       "AIC", "AICc",
                                       setdiff(names(merged_results), 
                                               c("ID", "run_date", 
                                                 "run_minutes", "observations",
                                                 "completeness", 
                                                 "AIC", "AICc")))]
  return(merged_results)
}

#### RUN A SINGLE MODEL
# by: JNatali
# on: 17 Nov 2024
# purpose: run a single model and track runtime
# returns: model_result, a dataframe with model summary stats (from glance()) 
#                         and model runtime
run_single_model <- function(response_matrix, param_list, model_id){
  
  # map well_id to row number
  well_index_dataframe <- as.data.frame(response_matrix) %>%
    mutate(row_index = row_number()) %>% #add row_index column
    select(well_id, row_index) %>% # select only well_id and row_index
    rename(term = well_id, estimate = row_index) #rename to match summary (below)
  
  ## FINAL response_matrix prep prior to passing model
  # strip header row and well_id column from response_matrix
  colnames(response_matrix) <- NULL
  response_matrix <- response_matrix[,-1]
  # ensure it's all numeric
  response_matrix <- apply(response_matrix, 2, as.numeric)
  
  # Track runtime
  start_time <- Sys.time()
  
  # Debug the model
  #model <- MARSS(response_matrix, model=param_list, control=list(maxit=number_iterations), fit=FALSE)
  
  # Fit the model
  model <- MARSS(response_matrix, model=param_list, control=list(maxit=number_iterations, trace=1))
  
  # Track runtime
  end_time <- Sys.time()
  execution_minutes <- as.numeric(difftime(end_time, start_time, units = "mins"))
 
  #model_summary <- tidy(model)
  # 0505 UPDATE Run 62: Skip MARSSparamCIs() 
  #model_summary <- tidy(model, method = "none")
  
  # 0505 UPDATE Run 63: Call MARSSparamCIs() with fewer bootstraps and in parallel
  model_CIs <- MARSSparamCIs(model, method = "parametric", nboot = 100, parallel = TRUE)
  
  # 0505 UPDATE Run 63: Use the above step to get model summary (for this model output csv)
  model_summary <- tidy(model_CIs)

  # append well_id info to summary
  model_summary <- bind_rows(model_summary, well_index_dataframe)
  
  # generate model results stats (for all model run summary csv)
  model_stats <- glance(model)
  
  # append AIC info to summary
  AIC_row <- data.frame(term="AIC", estimate = model_stats$AIC)
  model_summary <- bind_rows(AIC_row, model_summary)
  
  ## REPORT AND SAVE this model_summary for this model run as csv
  model_summary_filename = paste(formatted_date,"_",model_id,
                                 "_summary.csv",sep='')
  model_summary_filepath = paste(marss_results_dir, 
                                 model_summary_filename,
                                 sep='')
  write.csv(model_summary,model_summary_filepath, row.names=FALSE)
  
  ## SUMMARIZE AND MERGE summary with stats for "all model run" report 
  
  # Gather summary terms
  if (any(model_summary$term == "Q.diag")) {
    model_stats$Q.diag = model_summary$estimate[model_summary$term == "Q.diag"]
  } else model_stats$Q.diag = "N/A"
  
  if (any(model_summary$term == "Q.offdiag")) {
    model_stats$Q.offdiag = model_summary$estimate[model_summary$term == "Q.offdiag"]
  } else model_stats$Q.offdiag = "N/A"
  
  if (any(model_summary$term == "R.diag")) {
    model_stats$R.diag = model_summary$estimate[model_summary$term == "R.diag"]
  } else model_stats$R.diag = "N/A"
  
  if (any(model_summary$term == "U.1")) {
    model_stats$U.1 = model_summary$estimate[model_summary$term == "U.1"]
  } else model_stats$U.1 = "N/A"
  
  # return for analysis of full set of model runs
  return(cbind(model_stats, run_minutes = execution_minutes))
  
}

#### RUN ALL THE MODELS
# by: JNatali
# on: 17 Nov 2024
# purpose: run through all the models in the parameter setup csv,
#          generate and save results
# returns: model_dataframe
run_all_models <- function(response_matrix) {
  
   ### SETUP THE MODEL RUNS ###
   # setup the results dataframe
   results_dataframe <- data.frame() 
  
   # get the params for the MARSS model 
   model_param_dataframe <- get_model_parameters() # today's runs in the csv
   param_list_columns <- c("Z", "R", "U", "B", "Q", "C", "A")
   
   # LOOP through each row of the model IDs and params
   for (i in 1:nrow(model_param_dataframe)) {
     
     ## GET "timespan" param, can be = 'stacked', 'continuous' or 'each year'
     timespan_param <- model_param_dataframe$timespan[i]
     
     ## SET "number_iterations" for maxit param
     if (!is.na(model_param_dataframe$maxit[i])) {
      number_iterations <<- model_param_dataframe$maxit[i]
     }
     
     # check if need to restructure response data
     if (timespan_param == 'stacked') {
       response_matrix <- stack_groundwater_data(response_matrix)
     }
     
     # GET MARSS model parameters and name them appropriately
     row <- model_param_dataframe[i, param_list_columns, drop=FALSE]
     param_list <- as.list(row)
     names(param_list) <- param_list_columns
     
     # GET the model ID for this model run row
     model_ID = model_param_dataframe$ID[i]
     
     ### PREP THE RESPONSE MATRIX (groundwater data) ###
     ## GET completeness param and filter matrix
     model_response_matrix <- filter_incomplete_wells(response_matrix, 
                                                model_param_dataframe$completeness[i])
     
     # get and report # of states (i.e. groundwater wells)
     number_obs <- nrow(model_response_matrix)
     print(paste('MODEL RUN ',i,'number of observations: ', number_obs, sep=' '))
     
     # If 'each year', run for each year in year_range (global variable)
     if (timespan_param == 'each year'){
       for (year in year_range) {
         
         # print info for watching progress
         print(paste('PROCESSING year',year))
         
         # append year to model id (e.g. 2.2024)
         model_ID_year = model_ID + (year * 0.0001)
         
         # filter model_response_matrix to only this iteration's year
         # the select fn keeps well_id and all columns with the year
         year_response_matrix <- as.data.frame(model_response_matrix) %>%
           select(well_id, matches(paste0("^", year)))
         
         year_response_matrix <- as.matrix(year_response_matrix)
         
         ## SETUP a trycatch for errors so the model runs keep iterating
         year_result_dataframe <- tryCatch({
           
           # run the model for this year
          run_single_model(year_response_matrix, 
                                                     param_list, 
                                                     model_ID_year)
         }, error = function(e) {
           
           # print message and return NULL
           message(paste("ERROR at iteration", i, "in year", year, e$message))
           return(NULL)
         })
         
         if (!is.null(year_result_dataframe)) {
         
          # process results
          year_results <- process_model_results(year_result_dataframe,
                                                    model_param_dataframe[i, , drop=FALSE],
                                                    model_ID_year, number_obs)
         
          # add to results_dataframe
          results_dataframe <- rbind(results_dataframe, year_results)
         }
       }
     } else if (timespan_param == 'continuous') {
       # If 'continuous' (not year-by-year), run model as is, one time only.
       model_result_dataframe <- run_single_model(model_response_matrix, 
                                                  param_list, 
                                                  model_ID)
       # process results
       formatted_results <- process_model_results(model_result_dataframe,
                                                  model_param_dataframe[i, , drop=FALSE],
                                                  model_ID, number_obs)
       # add to results_dataframe
       results_dataframe <- rbind(results_dataframe, formatted_results) 
     
       } else {
       
       # If 'stacked' (each well represented per year), check if Z=grouped
        if (model_param_dataframe$Z[i] == 'grouped') {
          
          # iterator for printing info while processing
          i=0
          #z_list <- get_z_matrices_no_years(model_response_matrix)
          z_list <- get_z_matrices(model_response_matrix)
          
          # save original model_ID for reference within the z_list loop
          original_model_ID <- model_ID
          
          for (z_matrix in z_list){
           
            i=i+1
            
            # JN 2024_1226
            # update model_ID based on Z_grouping_id_list (a global var)
            # assign the ith item from Z_grouping_id_list
            if (!is.null(Z_grouping_id_list) &&
                i <= length(Z_grouping_id_list)) {
                    Z_id <- Z_grouping_id_list[i]
                    model_ID <- paste0(original_model_ID,"_",Z_id)
            }
            
            # print info for watching progress
            print(paste('PROCESSING Z round',i,'for model_ID',
                        model_ID,sep=' '))
          
            # replace 'grouped' in param_list with this z
            param_list$Z <- z_matrix
           
            # run model with z
            model_result_dataframe <- run_single_model(model_response_matrix, 
                                                      param_list, 
                                                      model_ID)
            # process results
            formatted_results <- process_model_results(model_result_dataframe,
                                                      model_param_dataframe[i, , drop=FALSE],
                                                      model_ID, number_obs)
            # add to results_dataframe
            results_dataframe <- rbind(results_dataframe, formatted_results) 
          }
        } else {
          # run model with z
          model_result_dataframe <- run_single_model(model_response_matrix, 
                                                     param_list, 
                                                     model_ID)
          # process results
          formatted_results <- process_model_results(model_result_dataframe,
                                                     model_param_dataframe[i, , drop=FALSE],
                                                     model_ID, number_obs)
          # add to results_dataframe
          results_dataframe <- rbind(results_dataframe, formatted_results) 
        }
     }
   }
   # save all results in csv
   start_id <- min(results_dataframe$ID)
   end_id <- max(results_dataframe$ID)
   # identify model_id and date in filename
   model_stats_filename = paste(formatted_date,"_",
                                start_id,"to",end_id,
                                "_stats.csv",sep='')
   
   # leverage directory names set at top of file
   # model_stats_filepath = paste(repository_dir, marss_script_dir,
   #                                model_stats_filename,
   #                                sep='')
   model_stats_filepath = paste(marss_results_dir, model_stats_filename,sep='')
   write.csv(results_dataframe,model_stats_filepath, row.names=FALSE)
   
   # return results
   return(results_dataframe)
}

#### ASSESS THE MODELS 
# by: JNatali
# on: 17 Nov 2024
# purpose: plot and compare model results, evaluate hypotheses
# returns:
# NOT YET DEFINED

# ------ MAIN PROCEDURAL SCRIPT ------
# Create matrix from data in groundwater_daily_FULL_COMBINED.csv
groundwater_data <- prepare_groundwater_data()
response_matrix <- load_response_data(groundwater_data)
results_dataframe <- run_all_models(response_matrix)
print("MODEL RUNS COMPLETE!!")