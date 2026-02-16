import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import math
from scipy.stats import linregress


# PART 1: SETUP & DATA LOADING

# Define Output Directory
output_csv_dir = os.path.join('..', '..', 'results', 'plots', 'groundwater', 'regression_comparison')
os.makedirs(output_csv_dir , exist_ok=True)
output_dir = output_csv_dir  + os.sep 

# Define Source File
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'groundwater', 'biweekly_manual')
SOURCE_FILE_PATTERN = "groundwater_2018_2024_weekly_matrix_STABLE.csv"
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)

print(f"Loading data from: {file_path}")
df = pd.read_csv(file_path)

# Separate Columns (ID vs Data)
id_cols = [c for c in df.columns if not str(c).startswith('20')]
week_cols = [c for c in df.columns if str(c).startswith('20')]

# Melt Data (Wide to Long)
df_long = df.melt(
    id_vars=id_cols, 
    value_vars=week_cols, 
    var_name='ISO_Week_Raw', 
    value_name='Level'
)

# Parse Dates
df_long['Year'] = df_long['ISO_Week_Raw'].astype(str).str[:4].astype(int)
df_long['Week'] = df_long['ISO_Week_Raw'].astype(str).str[4:].astype(int)

# Clean Numeric Data
df_long['Level'] = pd.to_numeric(df_long['Level'], errors='coerce')
df_long = df_long.dropna(subset=['Level'])

# Categorize Wells based on ID (e.g., 'KWR-1')
def categorize_well(val):
    meadow_map = {'K': "Kiln", 'E': "East"}
    plant_map = {'E': "Sedge", 'W': "Willow", 'H': "Mixed Herbaceous"}
    zone_map = {'R': "Riparian", 'T': "Terrace", 'F': "Fan"}
    try:
        codes = str(val).strip().split('-')[0]
        if len(codes) < 3: return pd.Series([None, None, None])
        m, p, z = codes[0], codes[1], codes[2]
        if (m in meadow_map and p in plant_map and z in zone_map):
            return pd.Series([meadow_map[m], plant_map[p], zone_map[z]])
        return pd.Series([None, None, None])
    except: return pd.Series([None, None, None])

df_long[['Site', 'Plant_Type', 'Zone']] = df_long['well_id'].apply(categorize_well)
df_long = df_long.dropna(subset=['Site', 'Plant_Type', 'Zone'])


# PART 2: STATISTICAL ANALYSIS (Regression)

# Split Data: Event (2021) vs Baseline (Others)
drought_year = 2021
non_drought_data = df_long[df_long['Year'] != drought_year].copy()
drought_data = df_long[df_long['Year'] == drought_year].copy()

# Aggregate Non-Drought Data (Create Synthetic "Normal" Year)
baseline_agg = non_drought_data.groupby(['well_id', 'Week'])['Level'].mean().reset_index()

# Helper: Linear Regression
def get_stats(data):
    # Need at least 3 points for a valid line
    if len(data) < 3: return np.nan, np.nan
    slope, _, r_val, _, _ = linregress(data['Week'], data['Level'])
    return slope, r_val**2

# Calculate Stats for Baseline
baseline_stats = []
for well, group in baseline_agg.groupby('well_id'):
    slope, r2 = get_stats(group)
    baseline_stats.append({'well_id': well, 'Slope_NonDrought': slope, 'R2_NonDrought': r2})

# Calculate Stats for Drought
drought_stats = []
for well, group in drought_data.groupby('well_id'):
    slope, r2 = get_stats(group)
    drought_stats.append({'well_id': well, 'Slope_Drought': slope, 'R2_Drought': r2})

# Merge and Compare
baseline_df = pd.DataFrame(baseline_stats)
drought_df = pd.DataFrame(drought_stats)
comparison = pd.merge(baseline_df, drought_df, on='well_id')

# METRIC: Similarity Score (Absolute Difference)
comparison['Slope_Diff'] = comparison['Slope_Drought'] - comparison['Slope_NonDrought']
comparison['Similarity_Score'] = comparison['Slope_Diff'].abs()

# Add Metadata back
meta = df_long[['well_id', 'Plant_Type', 'Zone']].drop_duplicates('well_id')
comparison = pd.merge(comparison, meta, on='well_id')

valid_wells = comparison.copy()

# Sort by Similarity (Most stable on top)
valid_wells = valid_wells.sort_values('Similarity_Score', ascending=True)
top_7 = valid_wells.head(7) # Using top 7 for better sample size


# PART 3: DETERMINE WINNERS FROM TOP 7

print("\n--- Top 7 Most Stable Wells Analysis ---")

# 1. Count by Plant Type
plant_counts = top_7['Plant_Type'].value_counts()
winning_plant = plant_counts.idxmax()
plant_count = plant_counts.max()

# 2. Count by Hydrozone
zone_counts = top_7['Zone'].value_counts()
winning_zone = zone_counts.idxmax()
zone_count = zone_counts.max()

print("\nTop 7 Breakdown:")
print(f"Most Prevalent Plant: {winning_plant} ({plant_count} out of 7)")
print(f"Most Prevalent Zone:  {winning_zone} ({zone_count} out of 7)")
print(f"\n>> WINNING COMBINATION: {winning_plant} - {winning_zone}")


# PART 4: SUBPLOTTING THE WINNERS


print(f"\nFetching ALL wells matching: {winning_plant} - {winning_zone}...")

# Filter the ORIGINAL dataset for all wells matching the winning combination
subset = df_long[
    (df_long['Plant_Type'] == winning_plant) & 
    (df_long['Zone'] == winning_zone)
].copy()

unique_wells = subset['well_id'].unique()
n_wells = len(unique_wells)
print(f"Found {n_wells} wells matching the winning combination.")

# Re-split this specific subset for plotting
# (We need the specific data for these wells, not just the stats)
subset_drought = subset[subset['Year'] == drought_year]
subset_nondrought = subset[subset['Year'] != drought_year]

# Aggregate Baseline for these specific wells
well_baseline_agg = subset_nondrought.groupby(['well_id', 'Week'])['Level'].mean().reset_index()

# Setup Grid
cols = 3
rows = math.ceil(n_wells / cols)
fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows), sharex=True, sharey=True)

# Flatten axes
if n_wells > 1:
    axes = axes.flatten()
else:
    axes = [axes]

print("Generating subplots...")

for i, well_id in enumerate(unique_wells):
    ax = axes[i]
    
    # Get Data for this well
    this_well_base = well_baseline_agg[well_baseline_agg['well_id'] == well_id]
    this_well_drought = subset_drought[subset_drought['well_id'] == well_id]
    
    # 1. Plot Baseline (Solid Blue)
    sns.lineplot(
        data=this_well_base,
        x='Week',
        y='Level',
        ax=ax,
        color='blue',
        label='Avg Non-Drought',
        linewidth=2,
        alpha=0.7
    )
    
    # 2. Plot Drought (Dashed Red)
    sns.lineplot(
        data=this_well_drought,
        x='Week',
        y='Level',
        ax=ax,
        color='red',
        label='2021 (Drought)',
        linewidth=2,
        linestyle='--'
    )
    
    # Formatting
    ax.set_title(well_id, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5)
    
    # Labels (Outer Only)
    if i >= (rows - 1) * cols:
        ax.set_xlabel("Week of Year")
    else:
        ax.set_xlabel("")
        
    if i % cols == 0:
        ax.set_ylabel("Depth (ft)")
    else:
        ax.set_ylabel("")

    # Legend (First plot only)
    if i == 0:
        ax.legend(loc='lower right', fontsize='small')
    else:
        if ax.get_legend():
            ax.get_legend().remove()

# Because sharey=True, inverting the first axis inverts them all.
axes[0].invert_yaxis() 

# Turn off empty subplots
for j in range(i + 1, len(axes)):
    axes[j].axis('off')

plt.suptitle(f"Most Stable (Regression) Category: {winning_plant} - {winning_zone}\n(Individual Well Performance: 2021 vs Normal Average)", fontsize=16, y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.95])

# Save
filename = f"subplot_regression_winner_{winning_plant}_{winning_zone}.eps"
save_path = os.path.join(output_dir, filename)
plt.savefig(save_path, bbox_inches='tight')
print(f"Saved figure to: {save_path}")

plt.show()
