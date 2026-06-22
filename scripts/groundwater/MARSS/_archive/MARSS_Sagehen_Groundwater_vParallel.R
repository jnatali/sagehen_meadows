##########  GROUNDWATER MARSS ANALYSIS SCRIPT  ##########  
# Author: Jennifer Natali, jennifer.natali@berkeley.edu
# Date Created: Sunday 17 November 2024
# 
# This script sets up and executes MARSS model(s) for groundwater level data.
# 
# This version supports:
# - a 'timespan' parameter that can be either 'continuous' or 'each year'
# - parallelized model runs
# 
# This code is under development and follows a functional programming paradigm.
# 
# Requires  data files:
# 1. RAW groundwater data (in cm) for all years: 'groundwater_biweekly_RAW.csv'
# 
# TODOs documented in github repo issue tracking.

# ------ IMPORTS ------

# Load libraries
library(MARSS)
library(lubridate)
library(dplyr)
library(foreach)
library(doParallel)

# ------ INITIALIZE GLOBAL VARIABLES ------
#### Info about the data
year_range <- c(2018, 2019, 2021, 2024)
# time limit for filtering groundwater observations
time_limit <- 12 # only include gw measurements prior to this time (i.e. noon)
# completeness limit for % of entries NA values per row
completeness_limit <- 0.88 # default, can be overridden by model params
# NOTE: at 0.85 13 wells removed, 0.8800->8 wells, 0.90->5 wells, at 0.95->2

# flag (binary) to keep or trim the first two weeks
# TODO: update code to trim first two weeks of EVERY YR (not just first year)
trim_first_two_weeks = FALSE

# today's date for running models from model parameter file listed for today
today <- Sys.Date()
formatted_date <- format(today, "%Y_%m%d")

# Setup directories and filepaths
home_dir='/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/'
repository_name = 'sagehen_meadows'
groundwater_data_dir = 'data/field_observations/groundwater/biweekly_manual/'
repository_dir = paste(home_dir, repository_name, '/', sep='')

groundwater_rawdata_filepath = paste(repository_dir, groundwater_data_dir,
                                     'groundwater_biweekly_FULL.csv',
                                     sep='')
groundwater_weekly_matrix_filepath = paste(repository_dir, groundwater_data_dir,
                                           'groundwater_weekly_matrix.csv',
                                           sep='')
marss_script_dir = 'scripts/groundwater/MARSS/'
model_parameter_filepath = paste(repository_dir, marss_script_dir,
                                 'MARSS_groundwater_parameters.csv',
                                 sep='')

# ------ DEFINE FUNCTIONS ------

#### PREPARE GROUNDWATER DATA
# by: JNatali
# on: 18 Nov 2024
# purpose: opens RAW groundwater data, manipulates into matrix form, saves it.
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
  
  isoweek_range <- min(groundwater$isoweek):max(groundwater$isoweek)
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
      weekly_matrix <- as.matrix(read.csv(groundwater_weekly_matrix_filepath),
                                  header=TRUE)
  } else {
    weekly_matrix <- as.matrix(weekly_matrix)
  }

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
#          returns them as a list of matrices
# returns: z_matrix_list, a list of matrices

# TODO: Consider other Z matrices:
#           SITE x PFT x HGMZ combo
#           well distance from Sagehen Creek (well across a transect)

# TODO: Use dynamic factor analysis to improve categorization of HGMZ / PFT
#       address uncertainty about categorization; see MARSS User Guide Ch 10.

get_z_matrices <- function(gw_data) {
  
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
  
  ## CREATE LIST OF MATRICES AND RETURN
  Z_matrix_list <- list(Z_site, Z_pft, Z_hgmz, Z_pftXhgmz)
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
  
  return(params)
}

#### PROCESS MODEL RESULTS
# by: JNatali
# on: 20 Nov 2024
# purpose: reformat the model run summaries prior to saving
# returns: merged_results dataframe with reformatted structure
process_model_results <- function(model_result_dataframe,
                                  model_param_dataframe,
                                  model_ID, number_states){
  
  # ASSIGN model ID and date to the result dataframe
  new_result_row <- data.frame(
    ID = model_ID,
    run_date = model_param_dataframe$run_date[i],
    states = number_states,
    completeness = model_param_dataframe$completeness[i],
    stringsAsFactors = FALSE)
  
  # Merge with "glance" summary from model run
  merged_results <- merge(new_result_row, 
                          model_result_dataframe, # "glance" dataframe + run_minutes
                          by = NULL)
  # reorder columns
  merged_results <- merged_results[, c("ID", "run_date", "run_minutes", 
                                       "states", "completeness", 
                                       "AIC", "AICc",
                                       setdiff(names(merged_results), 
                                               c("ID", "run_date", 
                                                 "run_minutes", "states",
                                                 "completeness", 
                                                 "AIC", "AICc")))]
  return(merged_results)
}

#### RUN A SINGLE MODEL
# by: JNatali
# on: 17 Nov 2024
# purpose: run a single models and track runtime
# returns: model_result, a dataframe with model summary stats (from glance()) 
#                         and model runtime
run_single_model <- function(response_matrix, param_list, model_id){

  # set max iterations
  number_iterations <- 10000
  
  ## FINAL response_matrix prep prior to passing model
  # strip header row and well_id column from response_matrix
  colnames(response_matrix) <- NULL
  response_matrix <- response_matrix[,-1]
  # ensure it's all numeric
  response_matrix <- apply(response_matrix, 2, as.numeric)
  
  # Track runtime
  start_time <- Sys.time()
  
  # Fit the model
  model <- MARSS(response_matrix, model = param_list, control=list(maxit=number_iterations))
  
  # Track runtime
  end_time <- Sys.time()
  execution_minutes <- as.numeric(difftime(end_time, start_time, units = "mins"))
  
  # Save model summary as a csv 
  model_summary <- tidy(model)
  # identify model_id and date in filename
  model_summary_filename = paste(formatted_date,"_",model_id,
                                 "_summary.csv",sep='')
  
  # WARNING: will only work if Q is 'diagonal' in the param file
  if (any(model_summary$term == "Q.diag")) {
    Q_diag = model_summary$estimate[model_summary$term == "Q.diag"]
  } else Q_diag = "N/A"
  
  # leverage directory names set at top of file
  model_summary_filepath = paste(repository_dir, marss_script_dir,
                                   model_summary_filename,
                                   sep='')
  
  write.csv(model_summary,model_summary_filepath, row.names=FALSE)
  
  # generate model results stats
  model_stats <- glance(model)
  # return for analysis of full set of model runs
  return(cbind(model_stats, run_minutes = execution_minutes, Q.diag = Q_diag))
  
}

#### RUN ALL THE MODELS
# by: JNatali
# on: 17 Nov 2024
# purpose: run through all the models in the parameter setup csv,
#          generate and save results
# returns: model_dataframe
run_all_models <- function(response_matrix) {
  
   ### SETUP PARALLELIZATION ###
   # use all but two cores
   num_cores <- parallel::detectCores() - 2 
   # create and register the cluster
   cluster <- makeCluster(num_cores)
   registerDoParallel(cluster)
   
   ### SETUP THE MODEL RUNS ###

   # get the params for the runs 
   model_param_dataframe <- get_model_parameters() # today's runs in the csv
   param_list_columns <- c("Z", "R", "U", "B", "Q", "C", "A")
   
   # LOOP through each row of the model IDs and params
   # use "foreach" to parallelize the model runs
   results_dataframe <- foreach(i = 1:nrow(model_param_dataframe),
                                .combine=rbind) %dopar% {
     
     # GET model parameters and name them appropriately
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
     number_states <- nrow(model_response_matrix)

     ## GET timespan param and filter matrix
     timespan_param <- model_param_dataframe$timespan[i]
     
     # If 'each year', run for each year in year_range (global variable)
     # NOT parallelized (only outer loop is)
     if (timespan_param == 'each year'){
       all_year_results <- foreach(year=year_range) %do% {
         # append year to model id (e.g. 2.2024)
         model_ID_year = model_ID + (year * 0.0001)
         
         # filter model_response_matrix to only this iteration's year
         year_response_matrix <- model_response_matrix %>%
           select(matches(paste0("^", year)))
         
         # run the model for this year
         year_result_dataframe <- run_single_model(year_response_matrix, 
                                                    param_list, 
                                                    model_ID_year)
         # process results
         year_results <- process_model_results(year_result_dataframe,
                                                    model_param_dataframe,
                                                    model_ID_year, number_states)
       }
       # combine inner loop 'year' results
       formatted_results <- do.call(rbind, year_results)

     } else {
        # If 'continuous' (not 'year year'), run model as is, one time only.
       model_result_dataframe <- run_single_model(model_response_matrix, 
                                                  param_list, 
                                                  model_ID)
       # process results
       formatted_results <- process_model_results(model_result_dataframe,
                                                  model_param_dataframe,
                                                  model_ID, number_states)
 
     }
     # return results, so they'll be added to results_dataframe
     formatted_results
   }
   
   ### STOP CLUSTER ###
   stopCluster(cluster)
   
   ### SAVE ALL MODEL RUN RESULTS ###
   start_id <- min(results_dataframe$ID)
   end_id <- max(results_dataframe$ID)
   # identify model_id and date in filename
   model_stats_filename = paste(formatted_date,"_",
                                start_id,"to",end_id,
                                "_stats.csv",sep='')
   
   # leverage directory names set at top of file
   model_stats_filepath = paste(repository_dir, marss_script_dir,
                                  model_stats_filename,
                                  sep='')
   
   # write to csv
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
groundwater_data <- prepare_groundwater_data()
response_matrix <- load_response_data(groundwater_data)
Z <- get_z_matrices(response_matrix)
results_dataframe <- run_all_models(response_matrix)
