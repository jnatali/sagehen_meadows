#RIVERLAB: Creating Groundwater_BiWeekly.csv
#Author: Julia Nicholson
library(tidyverse) # a universe of tidy data packages
library(patchwork)
library(hash)


biweekly_raw <- read.csv("C:/Users/Hugh/Desktop/Riverlab/sagehen_meadows/data/field_observations/groundwater/Groundwater_BiWeekly_RAW.csv")
well_tops_to_ground <- read.csv("C:/Users/Hugh/Desktop/Riverlab/sagehen_meadows/data/field_observations/groundwater/Wells_Dimensions.csv")
meter_offsets <- read.csv("C:/Users/Hugh/Desktop/Riverlab/sagehen_meadows/data/field_observations/groundwater/Wells_Meter_Offsets.csv")

#change meter_id header
meter_offsets <- meter_offsets %>% 
  rename(
    meter_id = ï..meter_id
  )
#adding a row for meter v.070919, until we know that value, for now the offset will be 0.
#Also, adding a row for when there is now water (nw)
new_row <- data.frame("v.070919","10/13/20", 0.0, NA)
names(new_row) <-  c("meter_id", "date", "offset", "std_dev") 
nw_row <- data.frame("nw","10/13/20", 0.0, NA)
names(nw_row) <-  c("meter_id", "date", "offset", "std_dev") 
meter_offsets <- rbind(meter_offsets, new_row)
meter_offsets <- rbind(meter_offsets, nw_row)


#averaging the well top to ground per well
well_top_to_ground <- well_tops_to_ground %>%
  group_by(well_id) %>%
  summarise_at(vars(welltop_to_ground, total_well_length), mean, na.rm = TRUE)
well_top_to_ground <- as.data.table(well_top_to_ground)

#averaging the three measurements for each day per well
well_top_to_water <- biweekly_raw
well_top_to_water$timestamp <- as.Date(well_top_to_water$timestamp,format="%m/%d/%y %H:%M")

well_top_to_water <- well_top_to_water %>%
  group_by(well_id, timestamp, meter_id) %>% #keep the meter id. Assumes same meter per site per day
  summarise_at(vars(welltop_to_water, water_binary), mean, na.rm = TRUE)

#putting the meter and other data together, for calculating distance from ground to water
groundwater_biweekly <- merge(well_top_to_water, well_top_to_ground, by = "well_id")
groundwater_biweekly <- merge(groundwater_biweekly, meter_offsets, by = "meter_id", how = "left")
groundwater_biweekly <- groundwater_biweekly[
  with(groundwater_biweekly, order(well_id, timestamp)),
  ]

water_ground_col <- c()


test_ground <- groundwater_biweekly
test_ground$ground_to_water <- NA
test_ground[is.na(test_ground$welltop_to_water), "ground_to_water"] <- NA
#when there's no water in the well, we input the (ground to well height - full well height)
cond1 <- (is.na(test_ground$welltop_to_water) & !is.na(test_ground$welltop_to_ground) & !is.na(test_ground$total_well_length) & (test_ground$meter_id == "nw" | (!is.na(test_ground$water_binary) & test_ground$water_binary == 0)))
test_ground$diff <- -(test_ground$total_well_length - test_ground$welltop_to_ground)
test_ground[cond1, "ground_to_water"] <- test_ground[cond1, "diff"] 
#if we have all the appropriate measures, then calculate ground to water:
cond2<- (!is.na(test_ground$welltop_to_water) & !is.na(test_ground$welltop_to_ground) & !is.na(test_ground$meter_id))
test_ground$diff <- -(test_ground$welltop_to_water - test_ground$welltop_to_ground + test_ground$offset)
test_ground[cond2, "ground_to_water"] <- test_ground[cond2, "diff"]

groundwater_biweekly <- test_ground[, c(2, 3, 5, 11)]
groundwater_biweekly_full <- test_ground


#
#
#
#playing with individual wells
EEF1 <- groundwater_biweekly[groundwater_biweekly$well_id == "EEF-1",]


individual_wells <- hash()
for (wellname in unique(groundwater_biweekly$well_id)){
  individual_wells[[wellname]] <- groundwater_biweekly[groundwater_biweekly$well_id == wellname,]
}

observations_per_well <- hash()
for (wellname in names(individual_wells)){
  observations_per_well[[wellname]] <- nrow(individual_wells[[wellname]])
}

wells_with_20_obs <- hash()
for (wellname in names(individual_wells)){
  if (observations_per_well[[wellname]] == 20 ){
    wells_with_20_obs[[wellname]] <- individual_wells[[wellname]]
  }
}


