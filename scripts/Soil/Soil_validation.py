import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import math

# Define Source File
OUTPUT_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil','Update')
OUTPUT_FILE_PATTERN = "soil_survey_at_wells.csv"
output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE_PATTERN)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"Created directory: {OUTPUT_DIR}")

# Define Source File
SOURCE_DIR = os.path.join( '..','..', 'data', 'field_observations', 'soil')
SOURCE_FILE_PATTERN = "soil_survey_at_wells.csv"
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)

print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

df['start depth (cm)'] = df['start depth (in)'] * 2.54
df['stop depth (cm)'] = df['stop depth (in)'] * 2.54

df.to_csv(output_path, index=False)
print(f"Saved updated data to: {output_path}")


