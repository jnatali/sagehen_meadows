##########  RAW LAI PROCESSING SCRIPT  ##########  
# Author: Wendy Feng
# Date Created: 03 December 2025
# 
# This script processes LAI data from the LP-80 Ceptometer
# 
# This code is under development and follows a procedural programming paradigm.
# 
# Requires  data files:
# 
# TODOs documented in github repo issue tracking.

# ------ IMPORTS ------

# Load libraries
library(dplyr)
library(lubridate)
library(readr)

# ------ INITIALIZE GLOBAL VARIABLES ------
# Set date for WAI measurement (no leaves on willow) 
willow_noleaf_date <- "2025-10-20"

# Setup directories and filepaths
home_dir='/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/'
repository_name = 'sagehen_meadows'
repository_dir = paste(home_dir, repository_name, '/', sep='')

LAI_data_dir = 'data/field_observations/vegetation/LAI/'
LAI_rawdata_filename = 'LAI_2025_RAW_FieldNotes.csv'
LAI_corrected_filename = 'LAI_2025_Corrected.csv'
LAI_script_dir = 'scripts/vegetation/LAI/'
LAI_results_dir = paste(home_dir, repository_name, '/results/vegetation/LAI/', sep='')

LAI_rawdata_file = paste(repository_dir, LAI_data_dir,
                                     LAI_rawdata_filename,
                                     sep='')
LAI_corrected_file = paste(repository_dir, LAI_data_dir,
                           LAI_corrected_filename,
                           sep='')

raw_data <- read_csv(LAI_rawdata_file)
names(raw_data)

# ------ DEFINE FUNCTIONS ------
# None

# ------ MAIN PROCEDURAL SCRIPT ------
## Drop raw data with no valid well id 
data <- raw_data %>%
  filter(Well_ID != "") 
#check
View(data)

## Identify willow wells
# create a new column: is_willow (binary)
# used substr(text, start_position, end_position) 
# to extract the 2nd character (indicating if it is a willow)
# verify Well_ID is a string/characters not factor 
class(raw_data$Well_ID)
str(raw_data$Well_ID)
data <- data %>%
  mutate(is_willow = substr(Well_ID, 2, 2) == "W")
#for convenience, creating a date column (with no time) 
data <- data %>%
  mutate(
    Date = as.Date(`Date and Time`, format = "%m/%d/%y %H:%M")
  )
#check 
View(data)

#willow WAI (woody area index) from 10-20-2025 data 
WAI<- data %>%
  filter(is_willow, Date == as.Date(willow_noleaf_date)) %>%
  select(Well_ID, WAI = `Leaf Area Index [LAI]`)
View(WAI)

data_corrected <- data %>%
  #left_join() to combine 2 dataframes based on common column
  left_join(WAI, by = "Well_ID") %>% 
  mutate(
    #corrected == TRUE only if willow and date before leafoff_date; WAI exists
    corrected = is_willow & Date < as.Date(willow_noleaf_date) & !is.na(WAI),
    #if corrected == TRUE, do the subtraction
    LAI_noWAI = if_else(corrected, `Leaf Area Index [LAI]` - WAI, `Leaf Area Index [LAI]`)
  )
View(data_corrected)

data_corrected <- rename(data_corrected,c('well_id'='Well_ID',
                                          'datetime'='Date and Time',
                                          'LAI'='Leaf Area Index [LAI]',
                                          'abovePAR'='Average Above PAR',
                                          'belowPAR'='Average Below PAR',
                                          'T'='Tau [T]',
                                          'Fb'='Beam Fraction [Fb]',
                                          'X'='Leaf Distribution [X]'))

LAI_Corrected <- data_corrected %>%
  select(
    well_id,
    datetime,
    LAI,
    LAI_noWAI,
    WAI,
    abovePAR,
    belowPAR,
    T,
    Fb,
    X,
    corrected
  )
View(LAI_Corrected)

write_csv(LAI_Corrected, LAI_corrected_file, append=TRUE)