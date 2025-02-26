# Sagehen Groundwater Scripts

## Sagehen Bi-Weekly Groundwater Scripts

## Sagehen Sub-Daily Groundwater Scripts
In subdaily directory, scripts to process RAW groundwater logger data.

### .py Scripts

#### subdaily_Processing_RawToGround.py
Takes RAW subdaily logger data and compensates for barometric pressure
Once compensated, translates water level above the pressure sensor to water level below ground
Uses manual readings to generate the needed offset, 
    then applies to all subdaily readings for the appropriate time period.

Saves output as: groundwater_subdaily_full.csv in the data/groundwater/subdaily folder.

Requires data files:  
    1. RAW logger data as .csv files in subdaily_dir with strict 
        naming convention and formatting  
    2. cut_times_file = groundwater_logger_times.csv (based on field notes)  
    3. barometric pressure data for the full time series that you want to process  

### .ipynb notebooks
These are older versions of code that've been wrapped into the subdaily_Processing_RawToGround.py script

Running all cells in the (which one?) .ipynb notebook will read every csv in the /data folder and cut the data using the rate of change. For each csv file, the script will plot and output how many rows were cut off of each end of the data (useful for validation). Can view plots in notebook and all are saved to plot folder. To run this script on new data, be sure to have the same directory setup.

# Sagehen Groundwater Data
Info on the groundwater data is in the data directory
- For biweekly, manually measured data, see this README.
- For subdaily data from data loggers, see this [README](https://github.com/jnatali/sagehen_meadows/blob/main/data/field_observations/groundwater/subdaily_loggers/README.md).

