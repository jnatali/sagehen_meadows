import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import math


# PART 1: SETUP & DATA LOADING

# Define Output Directory
output_csv_dir = os.path.join('..', '..', 'results', 'plot', 'groundwater', 'mean_comparison')
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

# Melt Data
df_long = df.melt(id_vars=id_cols, value_vars=week_cols, var_name='ISO_Week_Raw', value_name='Level')

# Parse Dates
df_long['Year'] = df_long['ISO_Week_Raw'].astype(str).str[:4].astype(int)
df_long['Week'] = df_long['ISO_Week_Raw'].astype(str).str[4:].astype(int)

# Clean Numeric Data
df_long['Level'] = pd.to_numeric(df_long['Level'], errors='coerce')
df_long = df_long.dropna(subset=['Level'])

# Categorize Wells
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


# PART 2: INDEPENDENT STABILITY ANALYSIS

drought_year = 2021
non_drought_data = df_long[df_long['Year'] != drought_year]
drought_data = df_long[df_long['Year'] == drought_year]

def find_winner(category_col):
    """
    1. Aggregates data by Category + Week.
    2. Calculates absolute difference (Normal vs Drought).
    3. Counts how many weeks each category had the smallest difference.
    4. Returns the name of the winning category.
    """
    print(f"Analyzing {category_col}...")
    
    # Aggregate
    base_agg = non_drought_data.groupby([category_col, 'Week'])['Level'].mean().reset_index()
    drought_agg = drought_data.groupby([category_col, 'Week'])['Level'].mean().reset_index()
    
    # Merge
    merged = pd.merge(base_agg, drought_agg, on=[category_col, 'Week'], suffixes=('_Base', '_Drought'))
    
    # Calculate Difference
    merged['Diff'] = (merged['Level_Base'] - merged['Level_Drought']).abs()
    
    # Find Weekly Winners (Lowest Difference)
    weekly_winners = merged.loc[merged.groupby("Week")["Diff"].idxmin()]
    
    # Count Wins
    counts = weekly_winners[category_col].value_counts()
    winner = counts.idxmax()
    wins = counts.max()
    
    print(f"  > Winner: {winner} ({wins} weeks most stable)")
    return winner

print("\n--- DETERMINING WINNERS ---")
winning_plant = find_winner('Plant_Type')
winning_zone = find_winner('Zone')

print(f"\nFinal Selection: {winning_plant} + {winning_zone}")


# PART 3: FILTER & PLOT COMBINED WINNERS (CORRECTED)

# Filter for wells that match BOTH winners
subset = df_long[
    (df_long['Plant_Type'] == winning_plant) & 
    (df_long['Zone'] == winning_zone)
].copy()

unique_wells = subset['well_id'].unique()
n_wells = len(unique_wells)

print(f"Found {n_wells} wells matching the winning combination.")

if n_wells == 0:
    print("WARNING: No wells exist with this specific Plant+Zone combination!")
else:
    # Prepare Well-Specific Baseline (Aggregate years for each well individually)
    subset_nondrought = subset[subset['Year'] != drought_year]
    well_baseline_agg = subset_nondrought.groupby(['well_id', 'Week'])['Level'].mean().reset_index()
    
    # Prepare Well-Specific Drought Data
    subset_drought = subset[subset['Year'] == drought_year]

    # Setup Grid
    cols = 3
    rows = math.ceil(n_wells / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows), sharex=True, sharey=True)

    # Flatten axes
    if n_wells > 1:
        axes = axes.flatten()
    else:
        axes = [axes]

    for i, well_id in enumerate(unique_wells):
        ax = axes[i]
        
        # Get Data for this well
        this_well_base = well_baseline_agg[well_baseline_agg['well_id'] == well_id]
        this_well_drought = subset_drought[subset_drought['well_id'] == well_id]
        
        # 1. Plot Baseline (Blue)
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
        
        # 2. Plot Drought (Red Dashed)
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

    # --- FIX: INVERT Y-AXIS ONCE ---
    # Moved outside the loop so it only executes once
    axes[0].invert_yaxis()

    # Turn off empty subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    plt.suptitle(f"Most Stable (Mean) Category: {winning_plant} - {winning_zone}\n(Individual Well Performance: 2021 vs Normal Average)", fontsize=16, y=0.99)
    plt.tight_layout()

    # Save
    filename = f"subplot_{winning_plant}_{winning_zone}.eps"
    save_path = os.path.join(output_dir, filename)
    plt.savefig(save_path)
    print(f"Saved figure to: {save_path}")

    plt.show()