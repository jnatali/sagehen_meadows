#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data transform script
Takes RAW subdaily logger data and compensates for barometric pressure
Once compensated, translates water level above the pressure sensor to water level below ground
Uses manual readings to generate the needed offset, 
then applies to all subdaily readings for the appropriate time period.

TODO: 
* 2021_0624 FIX cut times for 1-2 wells, see cut_times_file for notes
* 2021_0624 FIX missing baro data for 0715 to 0717 in 2018, file was not barometer data (see _BAD in baro_data_dir), consider using field station baro data 
* Look at barometric compensation script, why are 6 files empty?
* Look at several files with zero overlapping manual readings (note: if +/- 30 mins, capture 5 more valid files)
* EWR-1 2018-10-01 count: 0, KET-1 2019-09-04 count: 0, KWR-1 2018-10-01 count: 0, LHR-1 2019-10-05 count: 0
Created on Fri Jun 11 13:18:44 2021
@author: jnatali, alopez, zdamico
"""
# import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
import re # regexpression library to extract well id from filenames
#from glob import glob

### SETUP FLAGS 
##  for processing, logging, debugging and data validation
process_cut = False

debug_cut = False
debug_baro = False
debug_gtw = False

### SETUP DIRECTORY + FILE NAMES
project_dir = '/Users/jnat/Documents/Github/sagehen_meadows/'
gw_data_dir = project_dir + 'data/field_observations/groundwater/'
subdaily_dir = gw_data_dir + 'subdaily_loggers/Solinst_levelogger_all/'
cut_dir = gw_data_dir + 'subdaily_loggers/cut/'
baro_data_dir = gw_data_dir + 'subdaily_loggers/baro_data/'
compensated_dir = gw_data_dir + 'subdaily_loggers/baro_compensated/'
gtw_logger_dir = gw_data_dir + 'subdaily_loggers/relative_to_ground/'
os.makedirs(gtw_logger_dir,exist_ok=True)

cut_times_file = gw_data_dir + 'subdaily_loggers/groundwater_logger_times.csv'
cut_data_file = cut_dir+'cut_all_wells.csv'


### DEFINE FUNCTIONS 

## Consolidate all logger csv filesinto one dataframe    
def get_logger_dataframe():
    """Consolidate all logger csv filesinto one dataframe."""
    for f in os.listdir(subdaily_dir):
        log_df = pd.concat([pd.read_csv(f, header=11, encoding='ISO-8859-1')])
    log_df['DT'] = pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'])
    return log_df

## Plot subdaily logger dataframe
#  Assume dataframe has DT column converted to datetime
def plot_water_temp(logger,water_level_column_name,well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.plot(logger['DT'], logger[water_level_column_name])
    ax1.set_ylabel('Water Level', size=12)
    ax2.plot(logger['DT'], logger['TEMPERATURE'])
    ax2.set_ylabel('Temperature', size=12)

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(10)

    fig.suptitle('Groundwater Level and Temperature at Well '+ well_id, size=12)
    plt.show()
    
## Plot subdaily logger dataframe before/after cut times
#  Assume dataframe has DT column converted to datetime
def plot_water_temp_compare(before_df, after_df, water_level_column_name, well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.set_ylabel('Water Level', size=12)
    ax2.set_ylabel('Temperature', size=12)

    
    ax1.plot(before_df['DT'], before_df[water_level_column_name])
    ax2.plot(before_df['DT'], before_df['TEMPERATURE'])
    
    ax1.plot(after_df['DT'], after_df[water_level_column_name],'r')
    ax2.plot(after_df['DT'], after_df['TEMPERATURE'], 'r')
    

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(10)

    fig.suptitle('Before/After cut of GW Level and Temp at Well '+ well_id, size=12)
    plt.show()
    
## Plot subdaily logger dataframe before/after cut times
#  Assume dataframe has DT column converted to datetime
def plot_water_temp_compare(before_df, manual_df, after_df, water_level_column_name, well_id):
    fig, (ax1, ax2) = plt.subplots(figsize=(10, 5), nrows=2, sharex=True)
    ax1.set_ylabel('Water Level', size=12)
    ax2.set_ylabel('Temperature', size=12)

    
    ax1.plot(before_df['DT'], before_df[water_level_column_name])
    ax2.plot(before_df['DT'], before_df['TEMPERATURE'])
    
    ax1.plot(manual_df['DT'], manual_df[water_level_column_name],'g')
    ax2.plot(manual_df['DT'], manual_df['TEMPERATURE'], 'g')
    
    ax1.plot(after_df['DT'], after_df[water_level_column_name],'r')
    ax2.plot(after_df['DT'], after_df['TEMPERATURE'], 'r')
    

    for tick in ax1.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.yaxis.get_major_ticks():
        tick.label.set_fontsize(10)
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(10)

    fig.suptitle('Before/After cut of GW Level and Temp at Well '+ well_id, size=12)
    plt.show()
## Cut or trim logger data at front/back end of data
## to account for when logger not in the well.
## 
## for each logger file, cut times based on three factors:
## 1. the defined start/stop times in groundwater_logger_times file
## 2. based on an extreme temp change, signaling sensor out of water
## 3. (next step) the manual well measurement
def cut_logger_data():
    """Cut logger data at front/back to account for when logger not in the well."""
    
    
    ## new dataframes
    # to hold all well logger data
    cut_logger_df = pd.DataFrame()
    
    ## to track # of rows cutoff for each logger file
    cut_count_df = pd.DataFrame()
    
    ## from csv with start + end times for each logger deployment
    log_time_df = pd.read_csv(cut_times_file)
    log_time_df['start'] = pd.to_datetime(log_time_df['start'])
    log_time_df['end'] = pd.to_datetime(log_time_df['end'])
    

    ## process each logger deployment file
    for f in os.listdir(subdaily_dir):
        if f.endswith('.csv'):
        
            if debug_cut: print(f)
            
            # get well_id based on filename
            well_id = re.split('_20',f)[0]
                        
            log_df = pd.concat([pd.read_csv(subdaily_dir+f, header=11, encoding='ISO-8859-1')])
            log_df.insert(3, 'DT', pd.to_datetime(log_df['Date'] + ' ' + log_df['Time']))
            #log_df['DT'] = pd.to_datetime(log_df['Date'] + ' ' + log_df['Time'])
            
            # save log_df original version for comparison plot later
            orig_log_df = log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'})
            
            # plot raw data for well deployment
            # plot_water_temp(log_df,'LEVEL',' RAW '+ well_id)
            
            
            ## Calculate difference between raw datetime and field notes start_time and end_time
            #  select matching deployments from the field notes timing dataframe
            #  first by well_id, but this result may have timing for several deployments
            well_time_df = log_time_df[log_time_df['well_id'] == well_id]
            
            ## ERROR HANDLING if no time limits found for this well deployment in field notes
            if well_time_df.empty: 
                warning_str = 'WARNING: No time limits for ' + well_id + ': check if well name is correct. Exiting cut process.'
                print(warning_str)
                break
            
            #  select timing dataframe row from the range of times in the deployment logger file
            min_DT = log_df['DT'].min()
            max_DT = log_df['DT'].max()
            buffer = pd.Timedelta(hours=8)
            
            time_mask = ((well_time_df['start'] >= (min_DT - buffer)) & (well_time_df['end'] <= (max_DT + buffer)))
            well_time_df = well_time_df.loc[time_mask]
            
            ## ERROR HANDLING: only continue if one matching entry of start/stop times
            if well_time_df.shape[0] != 1:
                warning_str = 'WARNING: More/less than one row in well_time_df for ' + well_id + ', not clear which one to use. Exiting cut process.'
                print(warning_str)
                break
            
            
            # select logger data rows within start/end times from field notes
            # TODO: add/subtract 10 minutes from start/end times
            time_mask = (log_df['DT'] >= (well_time_df['start'].iloc[0] - pd.Timedelta(minutes=10))) & (log_df['DT'] <= well_time_df['end'].iloc[0] + pd.Timedelta(minutes=10))
            log_df = log_df.loc[time_mask]
            
            # take snapshot of dataframe to plot and validate later
            manual_log_df = log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'})
            
            ## Calculate temperature rate of change
            # temp change threshold that controls cutoff points
            change_threshold = well_time_df['temp_threshold'].iloc[0]
            if debug_cut: print(str(change_threshold))
            log_df['Rate of Change'] = np.append(np.abs((log_df['TEMPERATURE'].iloc[:-1].values - log_df['TEMPERATURE'].iloc[1:].values)/(10)), 0.0001)

            # Split data in half
            first = log_df.iloc[:int(log_df.shape[0]/2)]
            second = log_df.iloc[int(log_df.shape[0]/2):]
        
            # In first half, cut out all data before the last point that has a rate of change greater than the change threshold
            try:
                index = first.loc[(first['Rate of Change'] >= change_threshold), :].index[-1]
                first_cut = first.iloc[index:]
                if debug_cut: print('cutoff front end.')
            except IndexError as err:
                first_cut = first
                if debug_cut: print('Nothing to cut off front end.')
            
    
            # In second half, cut out all data after the first point that has a rate of change greater than the change threshold
            try:
                index = second.loc[(second['Rate of Change'] >= change_threshold), :].index[0]
                second_cut = second.loc[(second.index < index)]
                if debug_cut: print('cutoff backend.')
            except IndexError as err:
                second_cut = second
                if debug_cut: print('Nothing to cut off back end.')
        
            # Snip both halfs back together
            log_df = pd.concat((first_cut, second_cut), axis=0)
            log_df.rename(columns={'LEVEL': 'raw_LEVEL_m'}, inplace=True)
            
            # track cut info for each well
            track_df = pd.DataFrame(
                    {
                           'well_id':  well_id,
                           'front_cutoff': first.shape[0] - first_cut.shape[0],
                           'back_cutoff': second.shape[0] - second_cut.shape[0]
                    }, index=[0]
            )
            
            # append 
            cut_count_df = cut_count_df.append(track_df)
      
            # plot water level and temp for this well
            if debug_cut: plot_water_temp_compare(orig_log_df, manual_log_df, log_df,'raw_LEVEL_m',well_id)
            
            # save individual csv file with cut times
            log_df.to_csv(cut_dir+'cut_'+f, encoding='ISO-8859-1')
            
            # identify well_id and add to complete data frame for all, and save as csv
            log_df.insert(0, 'well_id', well_id)
            cut_logger_df = cut_logger_df.append(log_df)
    
    # cleanup logger data to save in human-readable format
    cut_logger_df.drop(['Date', 'Time', 'ms', 'Rate of Change'], axis=1, inplace=True)
    cut_logger_df.rename(columns={'DT': 'DateTime', 'TEMPERATURE': 'Temp_c'}, inplace=True)
    cut_logger_df.to_csv(cut_data_file, index=False)
    #cut_count_df.to_csv(cut_dir+'cut_count_'+str(change_threshold)+'.csv')
    cut_count_df.to_csv(cut_dir+'cut_count.csv')
    
    return cut_logger_df
    
## Consolidate all barometer CSV files into one dataframe
## Convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units
def get_baro_dataframe():
    """Consolidate all barometer CSV files into one dataframe, then convert LEVEL (kPa) to LEVEL (m); add a column for LEVEL (m); rename columns with units."""
    all_baro_data = pd.DataFrame()
    
    for f in os.listdir(baro_data_dir):
        if f.endswith('.csv'):
            if debug_baro: print(f)
            ## TODO: consider adding barometer well_id to dataframe
            new_baro = pd.read_csv(baro_data_dir + f, header=10, encoding='ISO-8859-1')
            
            if debug_baro: 
                print(str(len(new_baro)))
                test_b = new_baro
                test_b['DateTime'] = pd.to_datetime(test_b['Date'] + ' ' + test_b['Time'])
                str_b_range = 'min/max of new baro file time:' + str(min(test_b['DateTime'])) + ' to ' + str(max(test_b['DateTime']))
                print(str_b_range)
                
            all_baro_data = all_baro_data.append(new_baro,sort=True)
            
            if debug_baro: 
                print(str(len(all_baro_data))+ '\n\n')

    return all_baro_data

## Takes barometric pressure reading from the raw Solinst barologger
## and converts it from kPa of pressure to meters (m) of pressure
def convert_baro(baro_df):
    """Takes water level reading from the raw Solinst levelogger data, converts it from kPa of pressure to meters (m) above the sensor."""
    
    baro_df['baro_LEVEL_m'] = baro_df['LEVEL'] * 0.101972
    baro_df['DateTime'] = pd.to_datetime(baro_df['Date'] + ' ' + baro_df['Time'])
    
#    if debug_baro: 
#        str_b_range = 'min/max of baro time:' + str(min(baro_df['DateTime'])) + ' to ' + str(max(baro_df['DateTime']))
#        print(str_b_range)
    
    # cleanup baro data so column names clear, not carrying unneeded data
    baro_df.drop(['Date', 'Time', 'ms'], axis=1, inplace=True)
    baro_df.rename(columns={'LEVEL': 'baro_LEVEL_kPa', 'TEMPERATURE': 'baro_Temp_C'}, inplace=True)
    
    return baro_df

## Removes the barometric pressure (in meters) from the sensor water level
#  Assumes baro_df and gw_df are ('datetime64[ns]') type
def compensate_baro(baro_df, gw_df):
    """Removes the barometric pressure (in meters) from the sensor water level."""
    
    # merge baro and gw dataframes, only keeping relevant rows
    merge_df = baro_df.merge(gw_df, how='inner',on='DateTime')
    
    if debug_baro: 
        str_b_range = 'min/max of baro time:' + str(min(baro_df['DateTime'])) + ' to ' + str(max(baro_df['DateTime']))
        str_g_range = 'min/max of gw time:' + str(min(gw_df['DateTime'])) + ' to ' + str(max(gw_df['DateTime']))
        print(str_b_range)
        print(str_g_range)
        print('lost gw records after merge with baro: ' + str(len(gw_df) - len(merge_df)))
    
    # subtract baro data from gw data
    merge_df['compensated_LEVEL_m'] = merge_df['raw_LEVEL_m'] - merge_df['baro_LEVEL_m']
    
    # cleanup column names + order so human readable and save as csv
    merge_df.drop(['baro_LEVEL_kPa', 'baro_Temp_C'], axis=1, inplace=True)
    column_order = ['well_id', 'DateTime', 'raw_LEVEL_m', 'baro_LEVEL_m', 'compensated_LEVEL_m', 'Temp_c']
    merge_df = merge_df.reindex(columns=column_order)
    merge_df.to_csv(compensated_dir+'compensated_all_wells.csv', encoding='ISO-8859-1', index=False)

    return merge_df
    
## Convert baro-compensated water level from sensor 
## so that it's relative to the ground surface
## not the sensor level
## Use gw_df argument
def convert_relativeToGround(subdaily_df):
    """With groundwater dataframe as argument, convert baro-compensated water level from sensor so that it's relative to the ground surface, not the sensor level."""
    # set counts to track data quality
    deployment_count=0
    error_count=0
    
    # setup dataframe to capture all logger data with new ground_to_water_m column
    all_logger_df = pd.DataFrame()
    
    ## import manual groundwater data + setup for analysis
    biweek_df = pd.read_csv(gw_data_dir + 'biweekly_manual/groundwater_biweekly_full.csv')
    biweek_df['timestamp'] = biweek_df['timestamp'].astype('datetime64[ns]')
    

    ## START LOOP
    #  loop through each deployment
    #  defined as a sequential set of entries for each well
    
    subdaily_df = subdaily_df.sort_values(by=['well_id','DateTime'])
    
    #for consecutive, should = -10
    #subdaily_df['diff_prev'] = subdaily_df.groupby(['well_id'])['DateTime'].diff(-1).astype('timedelta64[m]')
    
    # if consecutive, 'diff_after' should = 10
    subdaily_df['diff_after'] = subdaily_df.groupby(['well_id'])['DateTime'].diff().astype('timedelta64[m]')
    
    #subdaily_df['check'] = np.where((subdaily_df.diff_prev==-10) | (subdaily_df.diff_after==10), True, False)
    #subdaily_df.to_csv(gw_data_dir+'test_groups.csv', encoding='ISO-8859-1', index=False)
   
    subd_g = subdaily_df.groupby(['well_id'])
    for w, g in subd_g:
        
        #g['deployment'] = g.diff_after.ne(10).cumsum()
        g.loc[:,'deployment'] = g.loc[:,'diff_after'].ne(10).cumsum()
        for d, deploy_g in g.groupby('deployment'):
            
            # get min+max time for each deployment; add/subtract 10 minutes from each to ensure we match all manual readings
            buffer = np.timedelta64(10,'m')
            minTime = min(deploy_g['DateTime']) - buffer
            maxTime = max(deploy_g['DateTime']) + buffer
    
            ## extract any manual readings for this well and datetime range
            this_well = biweek_df[biweek_df['well_id'] == w]
            this_well = this_well.set_index(['timestamp'])
            this_well_range = this_well.loc[minTime:maxTime]

    
            # ERROR HANDLING: report if no entries
            if (this_well_range.shape[0] == 0):
                if debug_gtw: print(w + ' ' + str(minTime.date()) + ' count: '+ str(this_well_range.shape[0]))
                # increment error_count
                error_count += 1
                # skip the rest of for loop, goto next file
                continue  
                
            if (this_well_range.shape[0] > 1):
                if debug_gtw: print(w + ' ' + str(minTime.date()) + ' count: '+ str(this_well_range.shape[0]))
                # keep only the first row
                this_well_range = this_well_range.drop_duplicates(subset='well_id', keep='first')
                #print(w + ' ' + str(minTime.date()) + ' count: '+ str(this_well_range.shape[0]))

  
            ## Find logger time entries that bracket the manual time entry (before and after)
            this_well_range.reset_index(level=0, inplace=True)
            
            # target datetime from manual data
            m_DT = this_well_range.iloc[0].timestamp
            # ground_to_water reading for target datetime; assume bi-weekly gtw is in centimers!!
            m_GTW = this_well_range.iloc[0].ground_to_water/100
    
            deploy_g.index = pd.DatetimeIndex(deploy_g.DateTime)
            l_closest_index = deploy_g.index.get_loc(m_DT,method='nearest')
            l_closest = deploy_g.iloc[l_closest_index]
            diff = l_closest.DateTime - m_DT
    
            # ERROR HANDLING: would be weird if diff is > 10 minutes
            if (diff > datetime.timedelta(minutes=10)):
                if debug_gtw: print(w + ' ' + str(minTime.date()) + ' logger-manual time diff is: '+ str(diff))
                # increment error_count
                error_count += 1
                continue
    
            # Interpolate GTW between times
            
            # use % time to determine if need prior or later logger data
            # if % time is negative, logger is before manual, get next logger reading
            # if % time is positive, logger is after manual, get prior logger reading
            percent_time = diff/datetime.timedelta(minutes=10)
            
            if (percent_time < 1): 
                l_bracket = deploy_g.iloc[l_closest_index+1]
            else: 
                l_bracket = deploy_g.iloc[l_closest_index-1]
            
            # calculate ground to water for l_closest
            shift_m = percent_time * (l_bracket['compensated_LEVEL_m'] - l_closest['compensated_LEVEL_m'])
            l_GTW = m_GTW + shift_m
            
            # sensor_level is the level of the sensor below the ground surface (which is 0)
            sensor_level = l_GTW - l_closest['compensated_LEVEL_m']
    
            # populate logger data frame with new column for Ground to Water Elevation in meters
            deploy_g.loc[:,'ground_to_water_m'] = sensor_level + deploy_g.loc[:,'compensated_LEVEL_m']
    
            # save dataframe to file
            # NOTE: re-order columns, why is it adding columns
            #subdaily_df = subdaily_df.drop(subdaily_df.columns[0:2],axis=1)
            #subdaily_df.to_csv(gtw_logger_dir+'gtw_'+f, encoding='ISO-8859-1',index=False)
            
            ## create singular csv for all logger data
            # add column to identify well
            #subdaily_df['well_id']=well_id
            
            # cleanup dataframe, drop unneeded columns
            deploy_g.drop(['diff_after'], axis=1, inplace=True)
            
            # append to singular all logger dataframe
            all_logger_df = all_logger_df.append(deploy_g)
            deployment_count += 1
    
    ## END LOOP
    
    # finished processing all logger files, now save singular file of all logger data
    # Re-order columns
    column_order = ['well_id', 'DateTime', 'deployment', 'ground_to_water_m', 'raw_LEVEL_m', 'baro_LEVEL_m', 'compensated_LEVEL_m', 'Temp_c']
    all_logger_df = all_logger_df.reindex(columns=column_order)
    all_logger_df.to_csv(gw_data_dir + 'subdaily_loggers/groundwater_subdaily_full.csv', encoding='ISO-8859-1', index=False)
    print ('GTW No Manual Entry ERRORS: ' + str(error_count) + ' of ' + str(file_count) + ' deployments.')

## Convert baro-compensated water level from sensor 
## so that it's relative to the ground surface
## not the sensor level
#def convert_relativeToGround():
#    """With no args, Convert baro-compensated water level from sensor so that it's relative to the ground surface, not the sensor level."""
#    # set counts to track data quality
#    file_count=0
#    error_count=0
#    
#    # setup a final df for logger data from all wells
#    all_logger_df = pd.DataFrame()
#    
#    ## import manual groundwater data + setup for analysis
#    manual_df = pd.read_csv(gw_data_dir + 'biweekly_manual/groundwater_biweekly_full.csv')
#    manual_df['timestamp'] = manual_df['timestamp'].astype('datetime64[ns]')
#    
#    ## iterate thru each subdaily logger file
#    ## and build dataframe of transformed water level data
#    for f in os.listdir(compensated_subdaily_dir):
#        
#        #print(f)
#        
#        # increment file_count
#        file_count += 1
#        
#        # import subdaily logger file
#        logger_df = pd.read_csv(compensated_subdaily_dir + f)
#        
#        # ERROR HANDLING: check if any entries before proceeding
#        if logger_df.empty: 
#            print('no entries in'+f)
#            # increment error_count
#            error_count += 1
#            # skip the rest of for loop, goto next file
#            continue    
#        
#        # use regular expression to extract well id from filename
#        # assumes filename follows naming convention: 
#        # 'compensated_cut_<wellid>_<year>_<daterange>.csv'
#        well_id = re.split('compensated_cut_',re.split('_20',f)[0])[1]
#        #print(well_id)
#        
#        ## get date range for logger_readings in the file
#        logger_df['DT'] = logger_df['DT'].astype('datetime64[ns]')
#        # add/subtract 10 minutes from each to ensure we have all helpful manual readings
#        minTime = min(logger_df['DT']) - np.timedelta64(10,'m')
#        maxTime = max(logger_df['DT']) + np.timedelta64(10,'m')
#        
#        ## extract any manual readings for this well and datetime range
#        manual_well = manual_df[manual_df['well_id'] == well_id]
#        manual_well = manual_well.set_index(['timestamp'])
#        manual_range = manual_well.loc[minTime:maxTime]
#    
#        
#        # ERROR HANDLING: report if no entries or >1 entry
#        if (manual_range.shape[0] == 0) | (manual_range.shape[0] > 1):
#            print(well_id + ' ' + str(minTime.date()) + ' count: '+ str(manual_range.shape[0]))
#            # increment error_count
#            error_count += 1
#            # skip the rest of for loop, goto next file
#            continue
#    
#        ## Find logger time entries that bracket the manual time entry (before and after)
#        manual_range.reset_index(level=0, inplace=True)
#        # target datetime from manual data
#        m_DT = manual_range.iloc[0].timestamp
#        # ground_to_water reading for target datetime
#        m_GTW = manual_range.iloc[0].ground_to_water
#        
#        logger_df.index = pd.DatetimeIndex(logger_df.DT)
#        l_closest_index = logger_df.index.get_loc(m_DT,method='nearest')
#        l_closest = logger_df.iloc[l_closest_index]
#        diff = l_closest.DT - m_DT
#        
#        # ERROR HANDLING: would be weird if diff is > 10 minutes
#        if (diff > datetime.timedelta(minutes=10)):
#            print(well_id + ' ' + str(minTime.date()) + ' logger-manual time diff is: '+ str(diff))
#            # increment error_count
#            error_count += 1
#            continue
#        
#        # Interpolate GTW between times
#        
#        # use % time to determine if need prior or later logger data
#        # if % time is negative, logger is before manual, get next logger reading
#        # if % time is positive, logger is after manual, get prior logger reading
#        percent_time = diff/datetime.timedelta(minutes=10)
#        if (percent_time < 1): 
#            l_bracket = logger_df.iloc[l_closest_index+1]
#        else: 
#            l_bracket = logger_df.iloc[l_closest_index-1]
#        
#        # calculate ground to water for l_closest
#        shift_m = percent_time * (l_bracket['Compensated Level'] - l_closest['Compensated Level'])
#        l_GTW = m_GTW + shift_m
#        
#        # sensor_level is the level of the sensor below the ground surface (which is 0)
#        sensor_level = l_GTW - l_closest['Compensated Level']
#        # populate logger data frame with new column for Ground to Water Elevation in meters
#        logger_df['ground_to_water_m'] = sensor_level + logger_df['Compensated Level']
#        
#        # save dataframe to file
#        # NOTE: re-order columns, why is it adding columns
#        logger_df = logger_df.drop(logger_df.columns[0:2],axis=1)
#        logger_df.to_csv(gtw_logger_dir+'gtw_'+f, encoding='ISO-8859-1',index=False)
#        
#        ## create singular csv for all logger data
#        # add column to identify well
#        logger_df['well_id']=well_id
#        
#        # append to singular all logger dataframe
#        all_logger_df = all_logger_df.append(logger_df)
#        
#    
#    # finished processing all logger files, now save singular file of all logger data
#    # NOTE: re-order columns, why is it adding columns
#    all_logger_df.to_csv(gw_data_dir + 'subdaily_loggers/groundwater_subdaily_full.csv')
#    print ('ERRORS: ' + str(error_count) + ' of ' + str(file_count) + ' files.')



### EXECUTE FUNCTIONS TO PROCESS LOGGER DATA

## Starts with individual raw Solinst logger files in the 'subdaily_dir' directory
## Use dataframe to pass data between functions
waterLevel_df = pd.DataFrame()
    
## 1. Cut logger entries when sensor not in the well, as indicated by temperature change
if process_cut: waterLevel_df = cut_logger_data()
else: 
    waterLevel_df = pd.read_csv(cut_data_file)
    waterLevel_df['DateTime'] = waterLevel_df.DateTime.astype('datetime64[ns]')

## 2. Compensate logger water level (m) based on barometer data (kPa)
waterLevel_df = compensate_baro(convert_baro(get_baro_dataframe()), waterLevel_df)

## 3. Convert water level from 'relative to sensor' to 'relative to ground surface elevation'.
convert_relativeToGround(waterLevel_df)
    