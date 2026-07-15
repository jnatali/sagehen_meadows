# install.packages("dplyr")
# install.packages("stringr")


library(aqp)
library(dplyr)
library(stringr)
library(here)


# Setup 
source(here("scripts", "groundwater", "well_utils.R"))

# Load data
df <- read.csv(
  here("data", "field_observations", "soil", "soil_survey_PROCESSED.csv")
)

# Add categories 
df <- get_well_categories(df)

df$start_depth_cm <- round(df$start_depth_cm)
df$stop_depth_cm <- round(df$stop_depth_cm)

# specify category of interest
categ <- "Fan"

# Filter a specific category
df <- df %>%
  filter(hydrogeo_zone == categ)

# -------------------------------------------------------------------------
# NEW: COLOR MAPPING & ORDERED CATEGORICAL LEGEND
# -------------------------------------------------------------------------

# 1. Standardize texture codes (uppercase, no trailing/leading spaces)
df$soil_texture_code <- toupper(trimws(df$soil_texture_code))

# 2. Define our custom brown gradient (ordered from lowest to highest clay)
texture_colors <- c(
  # Sands (Tier 1: Lightest sand/beige) ~10% max clay
  "COS"  = "#f5ecd5", "S"   = "#f5ecd5", "FS"   = "#f5ecd5", "VFS"  = "#f5ecd5",
  # Silt (Tier 2: Warm light silt) ~12% max clay
  "SI"   = "#decaae",
  # Loamy Sands (Tier 3: Rich sandy tan) ~15% max clay
  "LCOS" = "#c7a886", "LS"  = "#c7a886", "LFS"  = "#c7a886", "LVFS" = "#c7a886",
  # Sandy Loams (Tier 4: Warm sandy loam brown) ~20% max clay
  "COSL" = "#b0875f", "SL"  = "#b0875f", "FSL"  = "#b0875f", "VFSL" = "#b0875f",
  # Loams & Silt Loams (Tier 5: Classic loam brown) ~27% max clay
  "L"    = "#996538", "SIL" = "#996538",
  # Sandy Clay Loam (Tier 6: Medium warm clay-brown) ~35% max clay
  "SCL"  = "#82542b",
  # Clay Loams (Tier 7: Rich clay-loam brown) ~40% max clay
  "CL"   = "#6b421e", "SICL" = "#6b421e",
  # Sandy & Silty Clays (Tier 8: Dark clay brown) ~55-60% max clay
  "SC"   = "#47280e", "SIC" = "#47280e",
  # Clay (Tier 9: Deepest chocolate brown) ~100% max clay
  "C"    = "#000000",
  # Organic / Histosols (HO: Dark organic peat)
  "HO"   = "#808080",
  # Gravel / Coarse Fragment codes (GR: White horizon)
  "GR"   = "#FFFFFF"
)

# 3. Create an ordered factor of ONLY the codes present in your filtered dataset.
# This keeps the legend clean (no empty slots) while sorting them logically by clay!
present_codes <- unique(df$soil_texture_code)
ordered_levels <- names(texture_colors)[names(texture_colors) %in% present_codes]

# Handle any unexpected texture codes that aren't in our palette
unmapped_codes <- setdiff(present_codes, names(texture_colors))
ordered_levels <- c(ordered_levels, unmapped_codes)

df$soil_texture_code <- factor(df$soil_texture_code, levels = ordered_levels)

# 4. Generate the final color vector aligned exactly with our factor levels
active_colors <- texture_colors[ordered_levels]
active_colors[is.na(active_colors)] <- "#EAEAEA" # Fallback color if something is unmapped

# -------------------------------------------------------------------------

# Add the gravel calculation for the plot bubbles
df$gravel_amount_percent_hundred <- df$gravel_amount_percent * 100

# Add the space padding
df$plot_label <- paste0("    ", df$well_id)

# Convert the filtered data to a SoilProfileCollection
depths(df) <- well_id ~ start_depth_cm + stop_depth_cm

# Promote label to site data
site(df) <- ~ plot_label

# Format the category string for the file name 
# Converts to lowercase and replaces all spaces with underscores
formatted_categ <- gsub(" ", "_", tolower(categ))

# Create the final file name string (e.g., "wells_1_sedge.png")
file_name <- paste0("wells_1_", formatted_categ, ".png")

# Plot and Save
png(filename = here("results", "plots", "groundwater", "soils", file_name), 
    width = 1800, height = 2000, res = 150)

par(mar = c(0, 0, 8, 1)) 

plotSPC(df, 
        label = 'plot_label', # Tells aqp to use the custom column
        id.style = 'top',     # FORCE aqp to center labels above the column
        cex.names = 1,        
        cex.id = 0.85,        
        srt.id = 90,  
        offset.id = 1.5,        
        name.style = 'center-center',
        width = 0.3,
        depth.axis = FALSE,
        color = 'soil_texture_code', # Tells plotSPC to categorize using texture codes
        col.palette = active_colors, # Maps our custom clay-content colors to those categories
        col.label = "Soil Texture",
        hz.depths = TRUE,
        fixLabelCollisions = TRUE,
        depths.offset = 0.08,
        y.offset = 10,        # Pushes the profiles down by 10 units
        max.depth = 250,       # Extends canvas so shifted wells aren't cut off
        show.legend = TRUE    # Displays the clean, logically sorted legend!
        )

addVolumeFraction(df, 
                  colname = 'gravel_amount_percent_hundred', 
                  res = 10, cex.min = 0.1, cex.max = 0.5, 
                  pch = 1, col = "white")

dev.off()