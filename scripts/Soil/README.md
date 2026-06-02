# Sagehen Soil Profile Scripts

## Processing Soil Profile Data

## Script Descriptions
### soil_validation.py
- Checks and renames well_id with ..groundwater.well_utils module
- Standardizes gravel sub-class entries and soil texture naming
  
Requires  data files:
1. `data/field_observations/soil/RAW/soil_survey_at_wells.csv'
2. `well_renamed_id.csv` and `well_unique_id.txt` in `data/field_observations/groundwater/

Outputs resulting processed data to:
`data/field_observations/soil/soil_survey_at_wells_update_w_G.csv`

### plot_soil_horizons.R
<TODO: What it does.>

Requires data files:  
    1.  `data/field_observations/soil/soil_survey_at_wells_update_w_G.csv`

Outputs results to `groundwater_subdaily_full.csv` in `data/groundwater/subdaily/` 

## Archived Scripts

## Sagehen Soils Data
soil profile data is in the `data` directory

