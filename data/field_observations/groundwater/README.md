### Sagehen Groundwater Data



This directory contains groundwater level measurements for several meadows in Sagehen Basin during the growing season: May/June to Oct/Nov in 2018-2019.

Groundwater levels were sampled from three meadows (meadow_id). Within each meadow, shallow groundwater wells were located in a mapped hydrogeomorphic zone (HGMZ) and plant functional type (PFT). Some wells had been installed by a previous researcher (Allen-Diaz 1991) in randomly located cross-meadow transects, labeled A-E. See the key below plus description of Wells_Unique_Id.txt for naming conventions. Georeferenced well locations are defined in the data/instrumentation/Sagehen_Wells_Natali_3941.geojson file.

meadow_id:

* E = East

* K = Kiln

* L = Lower

HGMZ:

* R = riparian
* F = fan
* T = terrace

PFT:

* E = sedge
* H = mixed herbaceous
* W = willow
* F = mixed pine forest

#### Files and Data Model

*Groundwater_BiWeekly.csv* will contain the calculated groundwater level relative to the ground surface for each bi-weekly well measurement. The relative groundwater level will be an average of the three welltop_to_water readings in the *Groundwater_BiWeekly_RAW.csv*, subtract the welltop_to_ground level from *Wells_Dimensions.csv*  for the unique well_id and add the meter_offset from *Wells_Meter_Offsets.csv*  for the indicated meter_id.

*Groundwater_BiWeekly_RAW.csv*   contains unprocessed water level readings from the top of the well to the groundwater. Three readings were collected at each well on a bi-weekly basis. Each well has a unique id. Each reading has a timestamp and those with the same timestamp (listed in PDT, even if past official summer window) were collected within ~1 minute of each other. All readings should have occurred before 9am PDT. Some wells contained logging pressure transducers (then logger_binary = 1). Some wells were dry (then water_binary = 0). For each measurement, a meter_id is listed, which maps to an offset in the *wells_meterOffsets.csv* file. Variables in this file include: well_id, timestamp, welltop_to_water (in cm), logger_binary (true/false), water_binary (true/false) and meter_id.

*Wells_Meter_Offsets.csv*  contains the offset (in cm) that needs to be added to manual well measurements due to the gap between the water level meter and the ruler used to measure the groundwater level from the welltop. The offset was averaged from at least 30 measurements with the meter inserted into a glass container of water to determine the gap between the meter top and the water level. Variables in this file include: meter_id, date, offset (in cm) and std_dev (in cm).  



*Wells_Dimensions.csv*  contains measurements of the total_well_length in cm (from top to subsurface depth) and welltop_to_ground in cm from the top of the well to the ground surface. For   each well, multiple measurements may have been made so that an average can be used to calculate groundwater depth from the *average ground surface level*. The ground surface around each well was not level or smooth.



*Wells_Unique_Id.txt* is a master list of unique well identifiers for all wells measured in Sagehen basin. Suffixes of E, K, and L indicate a location in East, Kiln or Lower meadows. The second and third letter indicate the plant functional type and hydrogeomorphic process zone, respectively. Wells include those installed and measured by Allen-Diaz in the 1980s. These are indicated by the -X suffix. Otherwise, wells were installed by Jen Natali following a stratified sampling method according to hydrogeomorphic zone and plant functional type. 

*Wells_Missing_Data.xlsx* is an administrative file to help track needed data (well dimensions) to process all groundwater levels.

















