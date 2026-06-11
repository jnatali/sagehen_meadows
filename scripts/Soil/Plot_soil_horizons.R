
# install.packages("dplyr")
# install.packages("stringr")

library(aqp)
library(dplyr)
library(stringr)

setwd("/home/smittlek/JenProject/sagehen_meadows/")
# Setup 
# Make sure this path points exactly to where well_utils.R is saved
source("scripts/groundwater/well_utils.R")

# Load data
df <- read.csv("data/field_observations/soil/soil_survey_COMPLETE.csv")

# Add categories 
df <- get_well_categories(df)

df$start_depth_cm <- round(df$start_depth_cm)
df$stop_depth_cm <- round(df$stop_depth_cm)

#  Filter a specific category
east_meadow_df <- df %>%
  filter(hydrogeo_zone == "Fan")


# Convert the filtered data to a SoilProfileCollection
depths(east_meadow_df) <- well_id ~ start_depth_cm + stop_depth_cm

# Add the gravel calculation for the plot bubbles
east_meadow_df$gravel_amount_percent_hundred <- east_meadow_df$gravel_amount_percent * 100

# Plot and Save
png(filename = "results/plots/groundwater/soils/wells_Fan_HydroZone_TEST.png", 
    width = 1800, height = 2000, res = 150)


par(mar = c(0, 0, 1, 1))
plotSPC(east_meadow_df, 
        cex.name = 1,
        name.style = 'center-center',
        width = 0.3,
        depth.axis = FALSE,
        color = 'soil_texture_code', 
        hz.depths = TRUE,
        fixLabelCollisions = TRUE,
       depths.offset = 0.08
        )

addVolumeFraction(east_meadow_df, 
                  colname = 'gravel_amount_percent_hundred', 
                  res = 10, cex.min = 0.1, cex.max = 0.5, 
                  pch = 1, col = "white")

dev.off()
