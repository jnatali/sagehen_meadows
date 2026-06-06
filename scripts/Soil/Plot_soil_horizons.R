
# install.packages("dplyr")
# install.packages("stringr")

library(aqp)
library(dplyr)
library(stringr)

# Setup 
# Make sure this path points exactly to where well_utils.R is saved
source("scripts/groundwater/well_utils.R")

# Load data
df <- read.csv("data/field_observation/soil/Cleaned_wells_complete.csv")

# Add categories 
df <- get_well_categories(df)

#  Filter a specific category
east_meadow_df <- df %>%
  filter(hydrogeo_zone == "Fan")

# Convert the filtered data to a SoilProfileCollection
depths(east_meadow_df) <- well_id ~ start_depth_cm + stop_depth_cm

# Add the gravel calculation for the plot bubbles
east_meadow_df$gravel_amount_percent_hundred <- east_meadow_df$gravel_amount_percent * 100

# Plot and Save
png(filename = "results/plots/groundwater/soils/wells_Fan_HydroZone.png", 
    width = 1600, height = 1200, res = 150)



plotSPC(east_meadow_df, 
        name = 'soil_texture_code', 
        color = 'gravel_amount_percent', 
        label = 'well_id')

addVolumeFraction(east_meadow_df, 
                  colname = 'gravel_amount_percent_hundred', 
                  res = 10, cex.min = 0.1, cex.max = 0.5, 
                  pch = 1, col = "black")

dev.off()
