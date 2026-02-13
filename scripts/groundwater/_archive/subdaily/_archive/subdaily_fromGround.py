#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data transform script
Takes subdaily logger data (that is barometrically compensated)
Translates water level above the pressure sensor to water level below ground
Uses manual readings to generate the needed offset, 
then applies to all subdaily readings for the appropriate time period.

TODO: 
* Look at barometric compensation script, why are 6 files empty?
* Look at several files with zero overlapping manual readings (note: if +/- 30 mins, capture 5 more valid files)
* Add logic for files with >1 overlapping manual readings
* Consider renaming or re-ordering columns
* Integrate baro compensation script here
Created on Fri Jun 11 13:18:44 2021
@author: jnatali
"""
# import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
import re # regexpression library to extract well id from filenames

# setup directory names
project_dir = '/Users/jnat/Documents/Github/sagehen_meadows/'
gw_data_dir = project_dir + 'data/field_observations/groundwater/'
compensated_subdaily_dir = gw_data_dir + 'subdaily_loggers/baro_compensated/'
gtw_logger_dir = gw_data_dir + 'subdaily_loggers/relative_to_ground/'
os.makedirs(gtw_logger_dir,exist_ok=True)

# set counts to track data quality
file_count=0
error_count=0

# setup a final df for logger data from all wells
all_logger_df = pd.DataFrame()

## import manual data + setup for analysis
manual_df = pd.read_csv(gw_data_dir + 'biweekly_manual/groundwater_biweekly_full.csv')
manual_df['timestamp'] = manual_df['timestamp'].astype('datetime64[ns]')

### iterate thru each subdaily logger file
### and build dataframe of transformed water level data
for f in os.listdir(compensated_subdaily_dir):
    
    #print(f)
    
    # increment file_count
    file_count += 1
    
    # import subdaily logger file
    logger_df = pd.read_csv(compensated_subdaily_dir + f)
    
    # ERROR HANDLING: check if any entries before proceeding
    if logger_df.empty: 
        print('no entries in'+f)
        # increment error_count
        error_count += 1
        # skip the rest of for loop, goto next file
        continue    
    
    # use regular expression to extract well id from filename
    # assumes filename follows naming convention: 
    # 'compensated_cut_<wellid>_<year>_<daterange>.csv'
    well_id = re.split('compensated_cut_',re.split('_20',f)[0])[1]
    #print(well_id)
    
    ## get date range for logger_readings in the file
    logger_df['DT'] = logger_df['DT'].astype('datetime64[ns]')
    # add/subtract 10 minutes from each to ensure we have all helpful manual readings
    minTime = min(logger_df['DT']) - np.timedelta64(10,'m')
    maxTime = max(logger_df['DT']) + np.timedelta64(10,'m')
    
    ## extract any manual readings for this well and datetime range
    manual_well = manual_df[manual_df['well_id'] == well_id]
    manual_well = manual_well.set_index(['timestamp'])
    manual_range = manual_well.loc[minTime:maxTime]

    
    # ERROR HANDLING: report if no entries or >1 entry
    if (manual_range.shape[0] == 0) | (manual_range.shape[0] > 1):
        print(well_id + ' ' + str(minTime.date()) + ' count: '+ str(manual_range.shape[0]))
        # increment error_count
        error_count += 1
        # skip the rest of for loop, goto next file
        continue

    ## Find logger time entries that bracket the manual time entry (before and after)
    manual_range.reset_index(level=0, inplace=True)
    # target datetime from manual data
    m_DT = manual_range.iloc[0].timestamp
    # ground_to_water reading for target datetime
    m_GTW = manual_range.iloc[0].ground_to_water
    
    logger_df.index = pd.DatetimeIndex(logger_df.DT)
    l_closest_index = logger_df.index.get_loc(m_DT,method='nearest')
    l_closest = logger_df.iloc[l_closest_index]
    diff = l_closest.DT - m_DT
    
    # ERROR HANDLING: would be weird if diff is > 10 minutes
    if (diff > datetime.timedelta(minutes=10)):
        print(well_id + ' ' + str(minTime.date()) + ' logger-manual time diff is: '+ str(diff))
        # increment error_count
        error_count += 1
        continue
    
    # Interpolate GTW between times
    
    # use % time to determine if need prior or later logger data
    # if % time is negative, logger is before manual, get next logger reading
    # if % time is positive, logger is after manual, get prior logger reading
    percent_time = diff/datetime.timedelta(minutes=10)
    if (percent_time < 1): 
        l_bracket = logger_df.iloc[l_closest_index+1]
    else: 
        l_bracket = logger_df.iloc[l_closest_index-1]
    
    # calculate ground to water for l_closest
    shift_m = percent_time * (l_bracket['Compensated Level'] - l_closest['Compensated Level'])
    l_GTW = m_GTW + shift_m
    
    # sensor_level is the level of the sensor below the ground surface (which is 0)
    sensor_level = l_GTW - l_closest['Compensated Level']
    # populate logger data frame with new column for Ground to Water Elevation in meters
    logger_df['ground_to_water_m'] = sensor_level + logger_df['Compensated Level']
    
    # save dataframe to file
    # NOTE: re-order columns, why is it adding columns
    logger_df = logger_df.drop(logger_df.columns[0:2],axis=1)
    logger_df.to_csv(gtw_logger_dir+'gtw_'+f, encoding='ISO-8859-1',index=False)
    
    ## create singular csv for all logger data
    # add column to identify well
    logger_df['well_id']=well_id
    
    # append to singular all logger dataframe
    all_logger_df = all_logger_df.append(logger_df)
    

# finished processing all logger files, now save singular file of all logger data
# NOTE: re-order columns, why is it adding columns
all_logger_df.to_csv(gw_data_dir + 'subdaily_loggers/groundwater_subdaily_full.csv')
print ('ERRORS: ' + str(error_count) + ' of ' + str(file_count) + ' files.')


    
    
    