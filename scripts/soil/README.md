# Sagehen Soil Profile Scripts

## Processing Soil Profile Data
The following scripts plot soil profile data at named wells across Sagehen meadows

## Script Descriptions
### soil_validation.py
- Checks and renames well_id with ..groundwater.well_utils module
- Standardizes gravel sub-class entries and soil texture naming
  
Requires  data files:
1. `data/field_observations/soil/RAW/soil_survey_RAW.csv `
2. `well_renamed_id.csv` and `well_unique_id.txt` in `data/field_observations/groundwater/ `

Outputs resulting processed data to:
`data/field_observations/soil/soil_survey_VALIDATED.csv`
NOTE that the output was formerly:
`data/field_observations/soil/soil_survey_at_wells_update_w_G.csv`

### plot_soil_horizons.R
<TODO: What it does>

Requires data files:  
    1.  <TODO: Change to> `data/field_observations/soil/soil_survey_VALIDATED.csv`

Outputs plots to: 

<TODO: Note (if any) data manipulation> Data outputs to `<TODO: WHAT_HERE.csv>` in `data/field_observations/soil/`. Note could use _PROCESSED or _COMPLETE in file name to help indicate what step in the process.


