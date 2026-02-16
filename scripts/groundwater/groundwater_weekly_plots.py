import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Create the directory for saving files
output_dir = os.path.join('..', '..', 'results', 'plots', 'groundwater', 'seasonal')
os.makedirs(output_dir, exist_ok=True)
# FIX: Ensure directory string ends with a slash so it doesn't merge with filenames
output_dir = output_dir + os.sep 

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
    # Define the valid mapping dictionaries
    meadow_map = {'K': "Kiln", 'E': "East"}
    plant_map = {'E': "Sedge", 'W': "Willow", 'H': "Mixed Herbaceous"}
    zone_map = {'R': "Riparian", 'T': "Terrace", 'F': "Fan"}

    try:
        # Extract the prefix (e.g., 'KWR')
        codes = str(val).strip().split('-')[0]
        
        # Ensure we have at least 3 characters to unpack
        if len(codes) < 3:
            return pd.Series([None, None, None])
        
        m_code, p_code, z_code = codes[0], codes[1], codes[2]
        
        # Validation: Check if ALL codes exist in our maps
        if (m_code in meadow_map and 
            p_code in plant_map and 
            z_code in zone_map):
            
            return pd.Series([
                meadow_map[m_code], 
                plant_map[p_code], 
                zone_map[z_code]
            ])
        else:
            # If any code is unrecognized, return None
            return pd.Series([None, None, None])

    except Exception:
        # Catch-all for malformed strings or unexpected errors
        return pd.Series([None, None, None])

# Apply logic specifically to the 'well_id' column
df_long[['Site', 'Plant_Type', 'Zone']] = df_long[well_id_col].apply(categorize_well)
df_long = df_long.dropna(subset=['Site', 'Plant_Type', 'Zone'])
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


# --- TASK 1: MEAN LEVELS ACROSS ALL WELLS ---

t1_max = yearly_means['Level'].max() + 5
t1_min = yearly_means['Level'].min() - 5

# 1. INDIVIDUAL PLOT: Annual Lines
plt.figure(figsize=(10, 6))
sns.lineplot(data=yearly_means, x='Week', y='Level', hue='Year', palette=year_palette, marker='o')
plt.title('Mean GW Level by Year (All Wells)')
plt.ylabel('Depth Below Surface (cm)')
plt.grid(True, alpha=0.3)
# FIX: Use (Deepest, Shallowest) to invert manually
plt.ylim(t1_max, t1_min) 
plt.savefig(f"{output_dir}Mean_GW_Level_by_Year.eps", format='eps')
# plt.show()

# 2. INDIVIDUAL PLOT: Grand Mean Only
plt.figure(figsize=(10, 6))
sns.lineplot(data=grand_mean, x='Week', y='Level', color='black', linewidth=3, label='Grand Mean')
plt.title('Grand Mean (All Years Aggregated)')
plt.ylabel('Depth Below Surface (cm)')
plt.grid(True, alpha=0.3)
# FIX: Use (Deepest, Shallowest) to invert manually
plt.ylim(t1_max, t1_min) 
plt.savefig(f"{output_dir}GRAND_Mean_GW_Level_by_Year.eps", format='eps')
# plt.show()

# 3. COMBINED PLOT: Annual + Grand Mean Overlay
plt.figure(figsize=(10, 6))
# Plot annual lines with lower transparency (alpha) so the Grand Mean stands out
sns.lineplot(data=yearly_means, x='Week', y='Level', hue='Year', palette=year_palette, alpha=0.4, legend=False)
# Overlay the Grand Mean
sns.lineplot(data=grand_mean, x='Week', y='Level', color='black', linewidth=4, label='Grand Mean')
plt.title('Combined: Annual Trends vs. Grand Mean (All Wells)')
plt.ylabel('Depth Below Surface (cm)')
plt.legend()
plt.grid(True, alpha=0.3)
# FIX: Use (Deepest, Shallowest) to invert manually
plt.ylim(t1_max, t1_min) 
plt.savefig(f"{output_dir}COMBINED_Mean_GW_Level_by_Year.eps", format='eps')
plt.show() # Pausing here so you can check Task 1


# --- TASK 2: CATEGORIZED COMPARISONS ---

categories_to_plot = ['Site', 'Plant_Type', 'Zone']

for category_col in categories_to_plot:
    
    # Get valid unique values
    unique_cats = [c for c in df_long[category_col].unique() if c is not None]
    num_cats = len(unique_cats)
    
    # ---------------------------------------------------------
    # PART 1: PLOT SEPARATELY (Individual files)
    # ---------------------------------------------------------
    for cat_val in unique_cats:
        # Prepare Data
        subset = df_long[df_long[category_col] == cat_val]
        subset_annual = subset.groupby(['Year', 'Week'])['Level'].mean().reset_index()
        
        # Plot
        plt.figure(figsize=(8, 5))
        sns.lineplot(data=subset_annual, x='Week', y='Level', hue='Year', palette=year_palette, marker='.')
        
        # Formatting
        plt.title(f'Individual: {cat_val}')
        plt.grid(True, alpha=0.3)
        plt.ylabel('Depth Below Surface (cm)')
        
        # FIX: Manual inversion for single plots
        plt.gca().invert_yaxis() 
        
        # Save
        clean_name = str(cat_val).replace(" ", "_")
        plt.savefig(f"{output_dir}SEPARATE_{category_col}_{clean_name}.eps")
        plt.close() 

    # ---------------------------------------------------------
    # PART 2: PLOT TOGETHER (Subplots)
    # ---------------------------------------------------------
    # Create grid
    fig, axes = plt.subplots(1, num_cats, figsize=(5 * num_cats, 6), sharey=True)
    if num_cats == 1: axes = [axes] # Handle single-item case

    # Global scale for this comparison
    cat_subset = df_long[df_long[category_col].isin(unique_cats)]
    t2_max = cat_subset['Level'].max() + 5
    t2_min = cat_subset['Level'].min() - 5

    for i, cat_val in enumerate(unique_cats):
        ax = axes[i]
        type_data = df_long[df_long[category_col] == cat_val]
        
        # Calculate means
        type_annual = type_data.groupby(['Year', 'Week'])['Level'].mean().reset_index()
        
        # --- NEW LOGIC: Calculate Non-Drought Mean ---
        # Filter out 2021 first, then group by Week
        non_drought_data = type_data[type_data['Year'] != 2021]
        non_drought_mean = non_drought_data.groupby('Week')['Level'].mean().reset_index()

        # A. Plot Background Years (Non-Drought Years)
        if not non_drought_data.empty:
            # Alpha increased to 0.3 as requested
            sns.lineplot(data=type_annual[type_annual['Year'] != 2021], 
                         x='Week', y='Level', hue='Year', palette=year_palette, 
                         ax=ax, alpha=0.3, legend=False, linewidth=1.5)
        
        # B. Plot 2021 (Drought Year)
        drought_year = type_annual[type_annual['Year'] == 2021]
        if not drought_year.empty:
            sns.lineplot(data=drought_year, x='Week', y='Level', color=year_palette.get(2021, 'red'), 
                         ax=ax, linewidth=3, label='2021 (Drought)' if i == num_cats-1 else None)
        
        # C. Plot Non-Drought Mean (Black, Dashed)
        sns.lineplot(data=non_drought_mean, x='Week', y='Level', color='black', 
                     ax=ax, linewidth=2, linestyle='--', label='Non-Drought Avg' if i == num_cats-1 else None)
        
        # Formatting
        ax.set_title(cat_val, fontweight='bold')
        
        # FIX: Explicitly set (Deepest, Shallowest) to force inversion
        ax.set_ylim(t2_max, t2_min) 
        
        ax.grid(True, alpha=0.2)
        
        if i == 0:
            ax.set_ylabel('Depth Below Surface (cm)')
        else:
            ax.set_ylabel('')

    # Unified Title
    plt.suptitle(f'Comparison by {category_col}: 2021 vs Non-Drought Average', fontsize=16, y=1.02)
    plt.tight_layout()
    
    # Save
    plt.savefig(f"{output_dir}TOGETHER_Grid_{category_col}.eps", bbox_inches='tight')
    plt.show()

# --- TASK 3: DROUGHT (2021) vs NON-DROUGHT ---

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
# FIX: Explicitly set (Deepest, Shallowest) to force inversion
plt.ylim(t3_max, t3_min) 

# Save
save_path = f"{output_dir}drought_comparison_2021.eps"
plt.savefig(save_path, format='eps')
print(f"Saved: {save_path}")

plt.show()


# --- TASK 4: VISUALIZING SPREAD (StDev) ---

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
# FIX: Explicitly set (Deepest, Shallowest) to force inversion
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