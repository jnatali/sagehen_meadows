import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create the directory for saving files
output_dir = os.path.join('..', '..', 'data', 'scripts', 'groundwater', 'seasonal')
os.makedirs(output_dir, exist_ok=True)

# PART 1: DATA LOADING & PREP (Run this first)

# 1. Load Data
# Pandas reads the CSV. Row 0 becomes the headers.
# --- Define SOURCE file (where you read existing data FROM) ---
SOURCE_DIR = os.path.join('..', '..', 'data', 'field_observations', 'groundwater', 'biweekly_manual')

# 3. Base name of the files to search for
SOURCE_FILE_PATTERN = "groundwater_2018_2024_weekly_matrix_STABLE.csv"
file_path = os.path.join(SOURCE_DIR, SOURCE_FILE_PATTERN)

df = pd.read_csv(file_path)


# 2. Dynamic Column Separation
# We identify which columns are ID info and which are Data (Weeks)
id_cols = [c for c in df.columns if not str(c).startswith('20')]
week_cols = [c for c in df.columns if str(c).startswith('20')]

# ---------------------------------------------------------
# 3. MELT THE DATA (The Critical Step)
# ---------------------------------------------------------
# 'Melting' is the process of unpivoting a DataFrame from 
# Wide format (human-readable) to Long format (computer-readable).
#
# CURRENT STATE (Wide):
# well_id | 201801 | 201802 | ...
# W-001   |  10.5  |  12.1  | ...
#
# DESIRED STATE (Long):
# well_id | ISO_Week | Level
# W-001   | 201801   | 10.5
# W-001   | 201802   | 12.1
#
# EXPLANATION OF ARGUMENTS:
# id_vars:    The columns you want to KEEP as identifiers. 
#             These values will repeat for every week. (e.g., well_id)
# value_vars: The columns you want to UNPIVOT. 
#             These headers (201801, etc.) will vanish from the top 
#             and move into a new column rows.
# var_name:   New column that contains the 
#             iso week column. We call it 'ISO_Week_Raw' because it contains 
#             the raw string (e.g., "201801") which we must split later.
# value_name: New column that contains the 
#             grounwater levels, called 'Level'.

df_long = df.melt(
    id_vars=id_cols, 
    value_vars=week_cols, 
    var_name='ISO_Week_Raw', 
    value_name='Level'
)
# ---------------------------------------------------------

# 4. Clean Up Dates
# We parse the '201801' string into Year (2018) and Week (1).
df_long['Year'] = df_long['ISO_Week_Raw'].astype(str).str[:4].astype(int)
df_long['Week'] = df_long['ISO_Week_Raw'].astype(str).str[4:].astype(int)

# 5. Categorization Logic (Updated to match Canopy Script)
# Explicitly using 'well_id' as requested.
well_id_col = 'well_id' 

# Safety check: ensure the column actually exists before proceeding
if well_id_col not in df_long.columns:
    raise ValueError(f"Column '{well_id_col}' not found in CSV")

def categorize_well(val):
    # 1. Split by '-' to get the code prefix (e.g., 'KWR')
    # 2. Map letters to full names using dictionaries
    try:
        codes = str(val).strip().split('-')[0]
        m_code, p_code, z_code = codes[0], codes[1], codes[2]
        
        meadow = "Kiln" if m_code == 'K' else "East"
        plant = {"E": "Sedge", "W": "Willow", "H": "Mixed Herbaceous"}.get(p_code, p_code)
        zone = {"R": "Riparian", "T": "Terrace", "F": "Fan"}.get(z_code, z_code)
        
        return pd.Series([meadow, plant, zone])
    except:
        return pd.Series([None, None, None])
        print(f'Invalid data point found')

# Apply logic specifically to the 'well_id' column
df_long[['Site', 'Plant_Type', 'Zone']] = df_long[well_id_col].apply(categorize_well)
df_long['Level'] = pd.to_numeric(df_long['Level'], errors='coerce')



# DEFINE CONSISTENT COLORS

# We create a dictionary that maps every Year to a specific Color.
# This ensures that "2018" is always Blue (for example), even if
# 2018 is missing from some specific graphs.
unique_years = sorted(df_long['Year'].unique())
year_palette = dict(zip(unique_years, sns.color_palette("tab10", len(unique_years))))

# Calculate means so we can use them to set the axis limits
yearly_means = df_long.groupby(['Year', 'Week'])['Level'].mean().reset_index()
grand_mean = df_long.groupby('Week')['Level'].mean().reset_index()

# (Removed Global Y-Axis Limits Section here because we will calculate them 
# dynamically inside each task to avoid the "off-screen" issue)

print("Data Prep Complete.")


"""
# TASK 1: MEAN LEVELS ACROSS ALL WELLS

# --- CALCULATE LIMITS SPECIFICALLY FOR TASK 1 ---
# We calculate min/max only based on the 'yearly_means' data used in this plot
t1_max = yearly_means['Level'].max() + 5
t1_min = yearly_means['Level'].min() - 5

# 1. Setup Plot
fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

# Plot A: Annual Lines
# Note: We use 'palette=year_palette' instead of 'tab10' to enforce consistency
sns.lineplot(data=yearly_means, x='Week', y='Level', hue='Year', palette=year_palette, marker='o', ax=axes[0])
axes[0].set_title('Mean GW Level by Year (All Wells)')
axes[0].set_ylabel('Depth Below Surface (cm)')
axes[0].grid(True, alpha=0.3)
axes[0].invert_yaxis()             # Put 0 at the top (Surface)
axes[0].set_ylim(t1_max, t1_min)   # Apply limits specific to this task

# Plot B: Grand Mean
sns.lineplot(data=grand_mean, x='Week', y='Level', color='black', linewidth=3, ax=axes[1])
axes[1].set_title('Grand Mean (All Years Aggregated)')
axes[1].grid(True, alpha=0.3)
axes[1].invert_yaxis()             # Put 0 at the top
axes[1].set_ylim(t1_max, t1_min) 

plt.tight_layout()

# 2. Save
save_path = f"{output_dir}mean_gw_all_wells_and_grand_mean.eps"
plt.savefig(save_path, format='eps')
print(f"Saved: {save_path}")

plt.show()
"""
"""
# TASK 2: CATEGORIZED PLOTS

# Choose Category: 'Site', 'Plant_Type', or 'Zone'
category_col = 'Site' 

unique_cats = df_long[category_col].unique()

for cat_val in unique_cats:
    if cat_val is None: continue

    plt.figure(figsize=(10, 5))
    
    # Filter for specific category (e.g., just 'East' meadow)
    subset = df_long[df_long[category_col] == cat_val]
    
    # Skip if empty to avoid errors
    if subset.empty: continue

    # Calculate means for this subset
    subset_means = subset.groupby(['Year', 'Week'])['Level'].mean().reset_index()
    
    # --- CALCULATE DYNAMIC LIMITS FOR THIS SPECIFIC CATEGORY ---
    # This prevents the graph from going off-screen by tailoring the axis
    # to fit only the data present in this specific meadow/zone.
    local_max = subset_means['Level'].max() + 5
    local_min = subset_means['Level'].min() - 5
    
    # Plot
    # Note: Using 'year_palette' here ensures colors match Task 1
    sns.lineplot(data=subset_means, x='Week', y='Level', hue='Year', palette=year_palette, marker='.')
    
    plt.title(f'Mean GW Levels: {cat_val} ({category_col})')
    plt.ylabel('Depth Below Surface (cm)')
    plt.xlabel('ISO Week')
    plt.grid(True, alpha=0.3)
    
    # Axis Handling
    plt.gca().invert_yaxis() # Surface (0) at top
    plt.ylim(local_max, local_min) # Use LOCAL limits calculated above
    
    # Save with descriptive name
    clean_cat_name = str(cat_val).replace(" ", "_")
    save_path = f"{output_dir}mean_gw_{category_col}_{clean_cat_name}.eps"
    plt.savefig(save_path, format='eps')
    print(f"Saved: {save_path}")
    
    plt.show()

"""
# TASK 3: DROUGHT (2021) vs NON-DROUGHT

"""
drought_year = 2021
# Mark years as Drought vs Non-Drought
# This logic automatically buckets 2018, 2019, 2024, etc. as Non-Drought
df_long['Status'] = df_long['Year'].apply(lambda y: 'Drought (2021)' if y == drought_year else 'Non-Drought')
status_means = df_long.groupby(['Status', 'Week'])['Level'].mean().reset_index()

# --- CALCULATE LIMITS SPECIFICALLY FOR TASK 3 ---
t3_max = status_means['Level'].max() + 5
t3_min = status_means['Level'].min() - 5

plt.figure(figsize=(12, 6))

# Plot Non-Drought (Average of all other years)
sns.lineplot(
    data=status_means[status_means['Status']=='Non-Drought'], 
    x='Week', y='Level', color='grey', label='Non-Drought Average', linewidth=3
)

# Plot Drought Year
sns.lineplot(
    data=status_means[status_means['Status']=='Drought (2021)'], 
    x='Week', y='Level', color='red', label='Drought (2021)', linewidth=3
)

# Shade the difference
pivoted = status_means.pivot(index='Week', columns='Status', values='Level')
plt.fill_between(
    pivoted.index, 
    pivoted['Non-Drought'], 
    pivoted['Drought (2021)'], 
    color='red', alpha=0.1
)

plt.title('Drought Impact: 2021 vs Average of Normal Years')
plt.ylabel('Depth Below Surface (cm)')
plt.grid(True, alpha=0.3)

# Axis Handling
plt.gca().invert_yaxis()
plt.ylim(t3_max, t3_min) # Use limits specific to this comparison

# Save
save_path = f"{output_dir}drought_comparison_2021.eps"
plt.savefig(save_path, format='eps')
print(f"Saved: {save_path}")

plt.show()

"""
# TASK 4: VISUALIZING SPREAD (StDev)

# Calculate Mean and Standard Deviation per week
stats = df_long.groupby(['Year', 'Week'])['Level'].agg(['mean', 'std']).reset_index()

# --- CALCULATE LIMITS SPECIFICALLY FOR TASK 4 ---
# We must account for the standard deviation spread so the shading fits
t4_max = (stats['mean'] + stats['std']).max() + 5
t4_min = (stats['mean'] - stats['std']).min() - 5

# Create a 2x2 grid of subplots (for the 4 years)
# sharex/sharey ensures they all use the exact same scale for comparison
fig, axs = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
axs = axs.flatten()  # Flatten the 2D grid into a 1D list for easier looping

unique_years = sorted(stats['Year'].unique())

for i, year in enumerate(unique_years):
    # Safety check in case there are more than 4 years in data
    if i >= len(axs): break
    
    ax = axs[i]
    subset = stats[stats['Year'] == year]
    
    # Retrieve the consistent color for this year
    c = year_palette.get(year, 'black')
    
    # Plot line
    ax.plot(subset['Week'], subset['mean'], label=str(year), color=c, linewidth=2)
    
    # Plot spread (Mean +/- StdDev)
    ax.fill_between(
        subset['Week'], 
        subset['mean'] - subset['std'], 
        subset['mean'] + subset['std'], 
        color=c, alpha=0.15
    )
    
    # Subplot specific styling
    ax.set_title(f"Year: {year}", fontweight='bold')
    ax.grid(True, alpha=0.3)

# Axis Handling (Applied to all subplots via sharey/sharex)
# We set the limits on the first axis, and it propagates
axs[0].invert_yaxis()
axs[0].set_ylim(t4_max, t4_min) 

# Global Labels (placed on the figure object to avoid clutter)
fig.supylabel('Depth Below Surface (cm)')
fig.supxlabel('ISO Week')

plt.tight_layout()

# Save
save_path = f"{output_dir}annual_means_with_std_spread_subplots.eps"
plt.savefig(save_path, format='eps')
print(f"Saved: {save_path}")

plt.show()