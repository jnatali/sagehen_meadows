# Load the required package
library(aqp)

# Load the CSV file
soil_df <- read.csv("C:/Users/smitt/Downloads/soil_survey_at_wells_update_w_G.csv")

# Convert to SoilProfileCollection (Replace with your actual column names!)
depths(soil_df) <- well_id ~ start_depth_cm + stop_depth_cm

soil_df$gravel_amount_percent_hundred <- soil_df$gravel_amount_percent * 100

# Filter the data into the three groups
wells_F <- subset(soil_df, grepl("F", well_id))
wells_R <- subset(soil_df, grepl("R", well_id))
wells_T <- subset(soil_df, grepl("T", well_id))


# Create and save the plots to a specified folder

#  Save Wells containing 'F' 
png(filename = "D:/Research_Jen/Soil_survey/Graphs/wells_Fan_plot.png", width = 1600, height = 1200, res = 150)
plotSPC(wells_F, 
        name = 'soil_texture_code',          
	color = 'gravel_amount_percent',  
        label = 'well_id')        
addVolumeFraction(wells_F, colname = 'gravel_amount_percent_hundred', res = 10,
  cex.min = 0.1,
  cex.max = 0.5,
  pch = 1,
  col = "black")
dev.off()

# Save Wells containing 'R' 
png(filename = "D:/Research_Jen/Soil_survey/Graphs/wells_Riparian_plot.png", width = 1600, height = 1200, res = 150)
plotSPC(wells_R, 
        name = 'soil_texture_code',  
        color = 'gravel_amount_percent',  
        label = 'well_id') 
addVolumeFraction(wells_R, colname = 'gravel_amount_percent_hundred', res = 10,
  cex.min = 0.1,
  cex.max = 0.5,
  pch = 1,
  col = "black")
dev.off()


# Save Wells containing 'T' ---
png(filename = "D:/Research_Jen/Soil_survey/Graphs/wells_Terrace_plot.png", width = 1600, height = 1200, res = 150)
plotSPC(wells_T, 
        name = 'soil_texture_code',  
        color = 'gravel_amount_percent',  
        label = 'well_id') 
addVolumeFraction(wells_T, colname = 'gravel_amount_percent_hundred', res = 10,
  cex.min = 0.1,
  cex.max = 0.5,
  pch = 1,
  col = "black")
dev.off()