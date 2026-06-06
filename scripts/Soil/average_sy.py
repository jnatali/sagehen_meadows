import pandas as pd

soil_sy_dict = {
    'C': 0, 'SC': 0.04, 'SIC': 0, 'CL': 0.03, 'HO': 0,
    'SCL': 0.1, 'L': 0.08, 'GR': 0.28, 'SL': 0.18, 'XST': 0.28,
    'O': .28, 'FGR': 0.3, 'CGR': 0.28, 'S': 0.3, 'VCB': 0.28, 'MGR': 0.28
}

#  Load the data 
df_1 = pd.read_csv(r"D:\Research_Jen\Soil_survey\Cleaned_wells_complete.csv")

#  Data Cleaning
df_1 = df_1.dropna(subset=['well_id']).copy()

#  Math and Calculations
df_1['Sy'] = df_1['soil_texture_code'].map(soil_sy_dict)
df_1['thickness'] = df_1['stop_depth_cm'] - df_1['start_depth_cm']
df_1['Sy_weighted'] = df_1['Sy'] * df_1['thickness']

#  Grouping and Averaging
well_summary = df_1.groupby('well_id')[['Sy_weighted', 'thickness']].sum()
well_summary['average_Sy'] = well_summary['Sy_weighted'] / well_summary['thickness']


final_output = well_summary[['average_Sy']].reset_index()


final_output.to_csv(r"D:\Research_Jen\specific yield\Sy_information_COMPLETE.csv", index=False)

print("Success! Your CSV has been saved.")