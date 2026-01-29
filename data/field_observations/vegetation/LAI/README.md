### Sagehen LAI TO BE UPDATED --> WENDY, this is a template from Canopy Temperature, some things will apply to LAI and some things NOT. Also see the FIELD_METHODS.md in this folder. You don't need to repeat that info.
This directory contains canopy temperature readings from July to October 2025. 

Canopy temperatures were recorded with an Apogee sensor around wells in two meadows, representing three hydrogeomorphic zones (HGMZ) and three plant functional types (PFT).

Files in the RAW folder are files uploaded directly from the Apogee senesor. 

For groundwater well naming conventions, see the key below. 

#### Abbreviations used in our data model

##### meadow_id

* E = East
* K = Kiln

##### HGMZ

* R = riparian
* F = fan
* T = terrace

##### PFT

* E = sedge
* H = mixed herbaceous
* W = willow

#### Files and Data Model

##### File Naming Convention  
* TC_CORRECTED_YYYY-MM-DD_HHMM = data corrected for emissivity and plant_type in the field of view
* WORKING_YYYY-MM-DD_HHMM = data straight from the apogee sensor

##### Data Model: Columns for CSV
* Time; format M/DD/YYYY HH:MM
* Target; 
* Sensor Body;
* source_file; name of RAW data file from apogee sensor
* well_id; each well has a unique id.
* target_type; "plant", "bare ground", "thatch", or "sky"
* percent_cover; percent of plant_type in sensor's field of view
* Notes; notes from field book or recording

##### Additional Columns for TC_CORRECTED CSV
* corrected_Tc; plant temperature corrected for emissivity and other plant_type in the field of view
* Tc_Difference; difference of Target temperature and corrected_temperature
  






