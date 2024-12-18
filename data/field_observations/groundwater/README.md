### Sagehen Groundwater Data

This directory contains groundwater level measurements in Sagehen Basin during the growing season, May to Nov in 2018-2024.

Groundwater levels were sampled from three meadows (identified as *meadow_id*). 

Within each meadow, shallow groundwater wells were located in a mapped hydrogeomorphic zone (HGMZ) and plant functional type (PFT). 

Shallow groundwater wells were installed in each combination of HGMZs and PFTs. Some wells had been installed by a previous researcher (Allen-Diaz 1991) in randomly located cross-meadow transects, labeled A-E. 

Georeferenced well locations are defined in the *data/instrumentation/Sagehen_Wells_Natali_3941.geojson* file.

For groundwater well naming conventions, see the key below. All uniquely named wells are listed in *Wells_Unique_Id.txt*. 

#### Abbreviations used in our data model

##### meadow_id

* E = East
* K = Kiln
* L = Lower

##### HGMZ

* R = riparian
* F = fan
* T = terrace

##### PFT

* E = sedge
* H = mixed herbaceous
* W = willow
* F = mixed pine forest

#### Files and Data Model

##### File Naming Convention  
* _RAW = data straight from the field (notebook or recording)
* _WORK = data that's being processed (in progress), not yet validated
* _FULL = data that's been processed but NOT validated
* _FINAL = data that's been processed and validated


##### Groundater Files and Contents

*well_meter_offsets.csv*  contains the offset (in cm) that needs to be added to manual well measurements due to the gap between the water level meter and the ruler used to measure the groundwater level from the welltop. The offset was averaged from at least 30 measurements with the meter inserted into a glass container of water to determine the gap between the meter top and the water level. Variables in this file include: meter_id, date, offset (in cm) and std_dev (in cm).  

*well_dimensions.csv*  contains measurements of the total_well_length in cm (from top to subsurface depth) and welltop_to_ground in cm from the top of the well to the ground surface. For   each well, multiple measurements may have been made so that an average can be used to calculate groundwater depth from the *average ground surface level*. The ground surface around each well was not level or smooth.

*well_unique_id.txt* is a master list of unique well identifiers for all wells measured in Sagehen basin. Suffixes of E, K, and L indicate a location in East, Kiln or Lower meadows. The second and third letter indicate the plant functional type and hydrogeomorphic process zone, respectively. Wells include those installed and measured by Allen-Diaz in the 1980s. These are indicated by the -X suffix. Otherwise, wells were installed by Jen Natali following a stratified sampling method according to hydrogeomorphic zone and plant functional type. 

*well_characteristics.csv* contains info about each well, such as elevation.

###### in biweekly_manual

*groundwater_biweekly_FULL_Year.csv*  
Will contain the calculated groundwater level relative to the ground surface for each biweekly well measurement. 

The relative groundwater level will be an average of the three welltop_to_water readings in the *Groundwater_BiWeekly_RAW.csv*, subtract the welltop_to_ground level from *Wells_Dimensions.csv* for the unique well_id and add the meter_offset from *Wells_Meter_Offsets.csv* for the indicated meter_id.

*groundwater_biweekly_RAW_Year.csv*  
Contains unprocessed water level readings from the top of the well to the groundwater for the year(s) specified.

Variables in this file include: 
- well_id; each well has a unique id.
- date-timestamp; records date and time of well measurement.
- welltop_to_water (in cm); three readings were collected at each well on a bi-weekly basis. Each reading has a timestamp and those with the same timestamp (listed in PDT, even if past official summer window) were collected within ~1 minute of each other. All readings should have occurred before 9am PDT. 
- logger_binary (true/false); some wells contained logging pressure transducers (then logger_binary = 1).
- water_binary (true/false); some wells were dry at time of measurement (then water_binary = 0).
- meter_id; for each measurement, a meter_id is listed, which maps to an offset in the *wells_meterOffsets.csv* file.

###### in subdaily loggers



###### in archive

*Wells_Missing_Data.xlsx* is an archived administrative file to help track needed data (well dimensions) to process all groundwater levels. Working file is in Google Drive as [well_missing_data sheet](https://docs.google.com/spreadsheets/d/1VWjpe0lL2xAhl1Ogh15oLD59Xz053aVFRRPRLHZuETo/edit?gid=1784805402#gid=1784805402).

















