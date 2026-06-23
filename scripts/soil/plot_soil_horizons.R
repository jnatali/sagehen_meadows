# install.packages("dplyr")
# install.packages("stringr")

library(aqp)
library(dplyr)
library(stringr)
library(here)


# Setup 
source(here("scripts", "groundwater", "well_utils.R"))

# Load data
df <- read.csv(here("data", "field_observations", "soil", "soil_survey_PROCESSED.csv"))

# Add categories 
df <- get_well_categories(df)

df$start_depth_cm <- round(df$start_depth_cm)
df$stop_depth_cm <- round(df$stop_depth_cm)

# specify category of interedt
categ <- "Lodgepole Pine"

# Filter a specific category
df <- df %>%
  filter(plant_type == categ)

# Add the gravel calculation for the plot bubbles
df$gravel_amount_percent_hundred <- df$gravel_amount_percent * 100

# Add the space padding
df$plot_label <- paste0("    ", df$well_id)

# Convert the filtered data to a SoilProfileCollection
depths(df) <- well_id ~ start_depth_cm + stop_depth_cm

# Promote label to site data
site(df) <- ~ plot_label

# Format the category string for the file name 
# Converts to lowercase and replaces all spaces with underscores
formatted_categ <- gsub(" ", "_", tolower(categ))

# Create the final file name string (e.g., "wells_lodgepole_pine.png")
file_name <- paste0("wells_", formatted_categ, ".png")

# Plot and Save
png(filename = here("results", "plots", "groundwater", "soils", file_name), 
    width = 1800, height = 2000, res = 150)

par(mar = c(0, 0, 8, 1)) 

plotSPC(df, 
        label = 'plot_label', # Tells aqp to use the custom column
        id.style = 'top',     # FORCE aqp to center labels above the column
        cex.names = 1,        
        cex.id = 0.85,        
        srt.id = 90,  
        offset.id = 1.5,        
        name.style = 'center-center',
        width = 0.3,
        depth.axis = FALSE,
        color = 'soil_texture_code', 
        hz.depths = TRUE,
        fixLabelCollisions = TRUE,
        depths.offset = 0.08,
        y.offset = 10,        # Pushes the profiles down by 10 units
        max.depth = 250,       # Extends canvas so shifted wells aren't cut off
        )

addVolumeFraction(df, 
                  colname = 'gravel_amount_percent_hundred', 
                  res = 10, cex.min = 0.1, cex.max = 0.5, 
                  pch = 1, col = "white")

dev.off()
