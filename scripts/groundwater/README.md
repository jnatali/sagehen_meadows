# Sagehen Groundwater Scripts

## Sagehen Bi-Weekly Groundwater Scripts
### Ground_to_Water.py
In this directory, Ground_to_Water.py processes groundwater well readings to determine the groundwater
level relative to the ground surface. 

Requires 4 data files:
1. Unique well ids: `well_unique_id.txt`
2. Well Dimensions: `well_dimensions.csv`
3. RAW groundwater data (in cm) for all years: `groundwater_biweekly_RAW.csv`
4. Well meter offsets (in cm): `well_meter_offsets.csv`

Outputs resulting processed groundwater data to:
`data/field_observations/groundwater/plots/biweekly_manual/groundwater_biweekly_FULL.csv`

## Sagehen Sub-Daily Groundwater Scripts
### subdaily_Processing_RawToGround.py
In subdaily directory, script to process RAW groundwater logger data is subdaily_Processing_RawToGround.py.

It takes RAW subdaily logger data and compensates for barometric pressure
Once compensated, translates water level above the pressure sensor to water level below ground
Uses manual readings to generate the needed offset, 
    then applies to all subdaily readings for the appropriate time period.

Requires data files:  
    1. RAW logger data as .csv files in subdaily_dir with strict 
        naming convention and formatting  
    2. cut_times_file = `groundwater_logger_times.csv` (based on field notes)  
    3. barometric pressure data as .csv  
  
Outputs results to `groundwater_subdaily_full.csv` in `data/groundwater/subdaily/` 

## MARSS Analysis Scripts
### MARSS_Sagehen_Groundwater.R
To run MARSS model, the 'MARSS/MARSS_Sagehen_Groundwater.R' script creates a weekly groundwater dataset from the manual weekly groundwater measurements and the subdaily groundwater logger measurements. It uses parameters in the 'MARSS/MARSS_groundwater_parameters.csv' to define model run parameters.

TODO: Need clarity on which version of the .R script is the most recent. Due to performance issues, had tried parallelization in _vParallel.R version, but it seems that _0505.R version is the most up-to-date script. @jnatali needs to verify!

## Archived Scripts
### .ipynb notebooks
These are older versions of code that've been wrapped into the subdaily_Processing_RawToGround.py script

Running all cells in the (which one?) .ipynb notebook will read every csv in the /data folder and cut the data using the rate of change. For each csv file, the script will plot and output how many rows were cut off of each end of the data (useful for validation). Can view plots in notebook and all are saved to plot folder. To run this script on new data, be sure to have the same directory setup.

# Sagehen Groundwater Data
Info on the groundwater data is in the data directory
- For biweekly, manually measured data, see this README.
- For subdaily data from data loggers, see this [README](https://github.com/jnatali/sagehen_meadows/blob/main/data/field_observations/groundwater/subdaily_loggers/README.md).

