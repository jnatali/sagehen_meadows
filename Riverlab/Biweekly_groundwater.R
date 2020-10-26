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
#adding a row for when there is now water (nw)
nw_row <- data.frame("nw","10/13/20", 0.0, NA)
names(nw_row) <-  c("meter_id", "date", "offset", "std_dev") 
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
write.csv(groundwater_biweekly, "C:/Users/Hugh/Desktop/Riverlab/sagehen_meadows/data/field_observations/groundwater/groundwater_biweekly.csv")
write.csv(groundwater_biweekly_full, "C:/Users/Hugh/Desktop/Riverlab/sagehen_meadows/data/field_observations/groundwater/groundwater_biweekly_full.csv")


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

wells_with_18_or_more_obs <- hash()
for (wellname in names(individual_wells)){
  if (observations_per_well[[wellname]] > 17 ){
    wells_with_18_or_more_obs[[wellname]] <- individual_wells[[wellname]]
  }
}
#6 wells have exactly 20 observations
#17 wells have 18 or more observations
#25 wells have 15 or more observations

checking_weeks <- data.frame(matrix(NA, nrow = 20, ncol = 0))
for (wellname in keys(wells_with_20_obs)){
  #new.col <- wells_with_20_obs[[wellname]]$timestamp
  #cbind(checking_weeks, new.col)
  checking_weeks[wellname] <- wells_with_20_obs[[wellname]]$timestamp
  #checking_weeks[wellname] <- c(new.col, rep(NA, nrow(checking_weeks) - length(new.col)))
  #df$new.col <- c(new.col, rep(NA, nrow(df)-length(new.col)))
}

checking_weeks_18 <- data.frame(matrix(NA, nrow = 22, ncol = 0))
for (wellname in keys(wells_with_18_or_more_obs)){
  #new.col <- wells_with_20_obs[[wellname]]$timestamp
  #cbind(checking_weeks, new.col)
  checking_weeks_18[wellname] <- wells_with_18_or_more_obs[[wellname]]$timestamp
  #checking_weeks[wellname] <- c(new.col, rep(NA, nrow(checking_weeks) - length(new.col)))
  #df$new.col <- c(new.col, rep(NA, nrow(df)-length(new.col)))
}

### binning observations as per Albert's advice:
#i)
days_vec <- data.frame(matrix(NA, nrow = 509, ncol = 0))
days_vec["timestamp"] <- seq(as.Date("2018-05-31"), as.Date("2019-10-21"), "days") 

#ii)
#left joining with groundwater biweekly so the days that weren't measured have NAs
test <- left_join(days_vec, groundwater_biweekly, by = "timestamp")

#iii)
#assinging days to bins of every two weeks
test2 <- test %>% 
  mutate(week_fac=factor(lubridate::week(timestamp))) %>%
  mutate(bi_week_fac=factor((lubridate::week(timestamp) + (lubridate::year(timestamp) - 2018)*52)%/%2))

#cleaning up so separate observations are not in the same biweek:
#test2[test2$timestamp == as.Date("2018-10-01"),] <- 
test3 <- within(test2, bi_week_fac[timestamp == as.Date("2018-10-01")] <- factor(19))
test3 <- within(test3, bi_week_fac[timestamp == as.Date("2019-08-04") | timestamp == as.Date("2019-08-05")] <- factor(42)) 
test3 <- within(test3, bi_week_fac[timestamp == as.Date("2019-09-02")] <- factor(44)) 
groundwater_BY_BIWEEK <- test3

#now, we want all the wells side by side...
side_by_side <- data.frame(matrix(NA, nrow = 37, ncol = 0))
side_by_side["bi_week_fac"] <- as.factor(seq(11, 47))
for (wellname in unique(groundwater_BY_BIWEEK$well_id)){
  well_df_empty <- data.frame(matrix(NA, ncol = 0, nrow = 37))
  well_df_empty["bi_week_fac"] <- as.factor(seq(11, 47))
  well_df_vals <- groundwater_BY_BIWEEK[(!is.na(groundwater_BY_BIWEEK$well_id) & groundwater_BY_BIWEEK$well_id == wellname),][, c(4, 6)]
  well_df_vals <- well_df_vals %>% 
    group_by(bi_week_fac) %>%
    summarize(ground_to_water = mean(ground_to_water))
  well_df_vals <- as.data.frame(well_df_vals)
  well_df <- left_join(well_df_empty, well_df_vals, by = "bi_week_fac")
  names(well_df)[2] <- wellname
  side_by_side <- left_join(side_by_side, well_df, by = "bi_week_fac")
}
#remove the weeks where NO sites were observed:
side_by_side <- side_by_side[c(seq(1, 10), 13, seq(27, 29), seq(31, 37)),]

