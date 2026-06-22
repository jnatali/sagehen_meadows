### Sagehen Canopy Temperature
This directory contains canopy temperature data collected at Sagehen between July to October 2025. 

Canopy temperature was recorded with an Apogee sensor around wells in two meadows at well sites
representing three hydrogeomorphic zones (HGMZ) and three plant functional types (PFT).

Files in the RAW folder are files uploaded directly from the Apogee senesor. 

For groundwater well naming conventions, see the key of Abbreviations in the groundwater directory README.

#### Files and Data Model

##### File Naming Convention  
* canopy_temp_CORRECTED.csv = data corrected for non-veg ground cover in the field of view
* WORKING_YYYY-MM-DD_HHMM = data straight from the apogee sensor with field notes manually added

##### Data Model: Columns for WORKING_*CSV
* Time; format M/DD/YYYY HH:MM
* Target; 
* Sensor Body;
* source_file; name of RAW data file from apogee sensor
* well_id; each well has a unique id.
* target_type; "plant", "bare ground", "thatch", or "sky"
* percent_cover; percent of plant_type in sensor's field of view
* Notes; notes from field book or recording

##### Data Model for canopy_temp_CORRECTED
* Temp_canopy_C; plant temperature (in Celsius) corrected for emissivity and non-veg ground cover in the field of view
* Date; date of observation, but not time since aggregated from multiple observations
* well_id; follows conventions and unique naming id for groundwater wells, as documented in data/groundwater README

  






