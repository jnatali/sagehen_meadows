library(dplyr)
library(lubridate)
library(ggplot2)
library(tidyr)
library(readr)
library(plantecophys)

# =========================================================
# PART 1 — HYGROCHRON DAILY TIME SERIES
# =========================================================

# Step 1: Read hygrochron data
data <- read_csv("Desktop/hygrochron_2025_10min_per_well.csv") %>%
  mutate(
    datetime = mdy_hms(datetime),
    Date = as.Date(datetime)
  )
#check
head(data)
# Step 2: Remove unreasonable values
data_clean <- data %>%
  filter(
    RH_pct >= 0 & RH_pct <= 100,
    temperature_C > -40 & temperature_C < 60
  )
head(data_clean)
# Step 3: Daily averages by well
daily_well <- data_clean %>%
  group_by(Date, well_id) %>%
  summarise(
    Tave = mean(temperature_C, na.rm = TRUE),
    RHave = mean(RH_pct, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    VPD = RHtoVPD(RHave, Tave)
  )
head(daily_well)
#Step 3.5 (remove if not needed): remove beginning and end dates
date_range <- range(daily_well$Date, na.rm = TRUE)

daily_well <- daily_well %>%
  filter(
    Date >= (date_range[1] + 1),
    Date <= (date_range[2] - 1)
  )
# Step 4: Extract categories from well_id
daily_well <- daily_well %>%
  mutate(
    vegetation = case_when(
      substr(well_id, 2, 2) == "W" ~ "Willow",
      substr(well_id, 2, 2) == "H" ~ "Herbaceous",
      substr(well_id, 2, 2) == "E" ~ "Sedge",
      TRUE ~ NA_character_
    ),
    site = case_when(
      substr(well_id, 1, 1) == "E" ~ "East",
      substr(well_id, 1, 1) == "K" ~ "Kiln",
      TRUE ~ NA_character_
    ),
    geomorph = case_when(
      substr(well_id, 3, 3) == "R" ~ "Riparian",
      substr(well_id, 3, 3) == "T" ~ "Terrace",
      substr(well_id, 3, 3) == "F" ~ "Fan",
      TRUE ~ NA_character_
    )
  )
head(daily_well)
# Step 5: Summary series
#mean by veg type
veg_mean <- daily_well %>%
  group_by(Date, vegetation) %>%
  summarise(mean_VPD = mean(VPD, na.rm = TRUE), .groups = "drop")
head(veg_mean)

#overall_mean
overall_mean <- daily_well %>%
  group_by(Date) %>%
  summarise(mean_VPD = mean(VPD, na.rm = TRUE), .groups = "drop")

#mean by geomorph type
geomorph_daily <- daily_well %>%
  group_by(Date, geomorph) %>%
  summarise(mean_VPD = mean(VPD, na.rm = TRUE), .groups = "drop")

# Step 6: Colors by vegetation / well
willow_wells <- sort(unique(daily_well$well_id[daily_well$vegetation == "Willow"]))
herb_wells   <- sort(unique(daily_well$well_id[daily_well$vegetation == "Herbaceous"]))
sedge_wells  <- sort(unique(daily_well$well_id[daily_well$vegetation == "Sedge"]))

willow_cols <- setNames(
  colorRampPalette(c("#FFD84D", "#B8860B"))(length(willow_wells)),
  willow_wells
)
herb_cols <- setNames(
  colorRampPalette(c("#A1D99B", "#238B45"))(length(herb_wells)),
  herb_wells
)
sedge_cols <- setNames(
  colorRampPalette(c("#9ECAE1", "#2171B5"))(length(sedge_wells)),
  sedge_wells
)

well_colors <- c(willow_cols, herb_cols, sedge_cols)

# ---------------------------------------------------------
# PLOT 1: Daily VPD by well + overall mean
# Shows the VPD time series for every individual well (colored by
# vegetation type) overlaid with a single black line representing
# the overall mean VPD across all wells.
# ---------------------------------------------------------
ggplot() +
  geom_line(
    data = daily_well,
    aes(x = Date, y = VPD, group = well_id, color = well_id),
    linewidth = 0.8,
    alpha = 0.8
  ) +
  geom_line(
    data = overall_mean,
    aes(x = Date, y = mean_VPD),
    color = "black",
    linewidth = 1.4
  ) +
  scale_color_manual(values = well_colors) +
  theme_minimal() +
  labs(
    title = "Daily VPD by Well",
    subtitle = "Colored lines = individual wells; black = overall mean",
    x = "Date",
    y = "VPD (kPa)",
    color = "Well ID"
  )

# ---------------------------------------------------------
# PLOT 2: Faceted daily VPD by well
# Same daily VPD time series as Plot 1 but split into one panel
# ---------------------------------------------------------
ggplot(daily_well, aes(x = Date, y = VPD, group = well_id)) +
  geom_line(color = "darkblue", linewidth = 0.7) +
  facet_wrap(~ well_id, ncol = 4) +
  theme_minimal() +
  labs(
    title = "Daily VPD by Well",
    x = "Date",
    y = "VPD (kPa)"
  )

# ---------------------------------------------------------
# PLOT 3: Daily VPD by vegetation type
# Displays individual well VPD traces (thin, semi-transparent)
# alongside a thick line representing the daily mean VPD for
# each vegetation type (Willow, Herbaceous, Sedge)
# ---------------------------------------------------------
ggplot() +
  geom_line(
    data = daily_well,
    aes(x = Date, y = VPD, group = well_id, color = well_id),
    linewidth = 0.6,
    alpha = 0.5
  ) +
  geom_line(
    data = veg_mean,
    aes(x = Date, y = mean_VPD, color = vegetation),
    linewidth = 1.5
  ) +
  facet_wrap(~ vegetation, ncol = 1) +
  scale_color_manual(values = c(
    well_colors,
    "Willow" = "#C99800",
    "Herbaceous" = "#2E8B57",
    "Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  theme(legend.position = "none") +
  labs(
    title = "Daily VPD by Vegetation Type",
    subtitle = "Thin lines = wells; thick line = vegetation mean",
    x = "Date",
    y = "VPD (kPa)"
  )

# ---------------------------------------------------------
# PLOT 4: Daily mean VPD by geomorphic position
# Compares the daily mean VPD across the three geomorphic
# positions (Riparian, Terrace, Fan) on a single panel.
# ---------------------------------------------------------
geomorph_colors <- c(
  "Riparian" = "#6BAED6",
  "Terrace" = "#C2A878",
  "Fan" = "#FDBE85"
)

ggplot(geomorph_daily, aes(x = Date, y = mean_VPD, color = geomorph)) +
  geom_line(linewidth = 1) +
  scale_color_manual(values = geomorph_colors) +
  theme_minimal() +
  labs(
    title = "Daily Mean VPD by Geomorphic Position",
    x = "Date",
    y = "Mean VPD (kPa)",
    color = "Geomorph"
  )

# ---------------------------------------------------------
# PLOT 5: Daily mean VPD by vegetation type
# Cleaner version of the vegetation comparison — shows only the
# mean VPD per vegetation type (no individual well traces),
# ---------------------------------------------------------
ggplot(veg_mean, aes(x = Date, y = mean_VPD, color = vegetation)) +
  geom_line(linewidth = 1) +
  scale_color_manual(values = c(
    "Willow" = "#C99800",
    "Herbaceous" = "#2E8B57",
    "Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  labs(
    title = "Daily Mean VPD by Vegetation Type",
    x = "Date",
    y = "Mean VPD (kPa)",
    color = "Vegetation"
  )

# ---------------------------------------------------------
# OPTIONAL sanity check plots
# daily mean temperature and relative humidity for every well, with Willow wells highlighted in
# gold and all other wells shown in grey.
# ---------------------------------------------------------
daily_well <- daily_well %>%
  mutate(willow_group = ifelse(vegetation == "Willow", "Willow", "Other"))

ggplot(daily_well, aes(x = Date, y = Tave, group = well_id, color = willow_group)) +
  geom_line(alpha = 0.8, linewidth = 0.8) +
  scale_color_manual(values = c("Willow" = "#D4A017", "Other" = "grey75")) +
  theme_minimal() +
  theme(legend.position = "none") +
  labs(
    title = "Daily Mean Temperature by Well",
    x = "Date",
    y = "Temperature (°C)"
  )

ggplot(daily_well, aes(x = Date, y = RHave, group = well_id, color = willow_group)) +
  geom_line(alpha = 0.8, linewidth = 0.8) +
  scale_color_manual(values = c("Willow" = "#D4A017", "Other" = "grey75")) +
  theme_minimal() +
  theme(legend.position = "none") +
  labs(
    title = "Daily Mean Relative Humidity by Well",
    x = "Date",
    y = "Relative Humidity (%)"
  )

# =========================================================
# TABLE 1 — HYGROCHRON DAILY DATA
# One row per well per day. Contains the daily mean air
# temperature (Tave), relative humidity (RHave), and
# derived VPD, along with the well's vegetation type,
# site, and geomorphic position. The primary
# reference table for the hygrochron time series.
# =========================================================

table_hygro <- daily_well %>%
  select(
    Date,
    well_id,
    vegetation,
    site,
    geomorph,
    Tave,
    RHave,
    VPD
  ) %>%
  arrange(Date, well_id)

head(table_hygro)
# =========================================================
# PART 1.5 — Plot difference 
# =========================================================
# ---------------------------------------------------------
# PLOT 1: VPD difference by vegetation (reference = Willow)
# Two panels show (a) the daily raw difference in mean VPD
# between Willow and each of the other vegetation types
# (Herbaceous and Sedge), and (b) the cumulative sum of
# those differences over the season. Positive values mean
# Willow experienced higher VPD than the comparison group
# on that day. 
# ---------------------------------------------------------
veg_wide_vpd <- veg_mean %>%
  select(Date, vegetation, mean_VPD) %>%
  pivot_wider(names_from = vegetation, values_from = mean_VPD)

veg_wide_vpd <- veg_wide_vpd %>%
  mutate(
    diff_Willow_Herbaceous = Willow - Herbaceous,
    diff_Willow_Sedge = Willow - Sedge
  )
veg_diff_long_vpd <- veg_wide_vpd %>%
  select(Date, diff_Willow_Herbaceous, diff_Willow_Sedge) %>%
  pivot_longer(
    cols = starts_with("diff"),
    names_to = "comparison",
    values_to = "diff_value"
  )

ggplot(veg_diff_long_vpd, aes(x = Date, y = diff_value, color = comparison)) +
  geom_line(linewidth = 1) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "diff_Willow_Herbaceous" = "#2E8B57",
    "diff_Willow_Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  labs(
    title = "Daily VPD Difference from Willow",
    x = "Date",
    y = "VPD Difference (kPa)",
    color = "Comparison"
  )
veg_cum_diff_vpd <- veg_wide_vpd %>%
  arrange(Date) %>%
  mutate(
    cum_diff_Willow_Herbaceous = cumsum(ifelse(is.na(diff_Willow_Herbaceous), 0, diff_Willow_Herbaceous)),
    cum_diff_Willow_Sedge = cumsum(ifelse(is.na(diff_Willow_Sedge), 0, diff_Willow_Sedge))
  )

ggplot(veg_cum_diff_vpd, aes(x = Date)) +
  geom_line(aes(y = cum_diff_Willow_Herbaceous, color = "Herbaceous"), linewidth = 1.2) +
  geom_line(aes(y = cum_diff_Willow_Sedge, color = "Sedge"), linewidth = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Herbaceous" = "#2E8B57",
    "Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  labs(
    title = "Cumulative VPD Difference from Willow",
    x = "Date",
    y = "Cumulative Difference (kPa)",
    color = "Vegetation"
  )

# ---------------------------------------------------------
# PLOT 2: VPD difference by vegetation (reference = Mean)
# Similar to Plot 1 but uses the daily cross-vegetation mean
# as the reference instead of Willow. Positive values indicate
# a vegetation type was drier than average on that day. 
# ---------------------------------------------------------
veg_mean_all_vpd <- veg_mean %>%
  group_by(Date) %>%
  summarise(
    overall_mean = mean(mean_VPD, na.rm = TRUE),
    .groups = "drop"
  )

veg_mean_ref_vpd <- veg_mean %>%
  left_join(veg_mean_all_vpd, by = "Date") %>%
  mutate(
    diff_from_mean = mean_VPD - overall_mean
  ) %>%
  arrange(vegetation, Date) %>%
  group_by(vegetation) %>%
  mutate(
    cum_diff = cumsum(ifelse(is.na(diff_from_mean), 0, diff_from_mean))
  ) %>%
  ungroup()

ggplot(veg_mean_ref_vpd, aes(x = Date, y = diff_from_mean, color = vegetation)) +
  geom_line(linewidth = 1.1) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Willow" = "#C99800",
    "Herbaceous" = "#2E8B57",
    "Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  labs(
    title = "Daily VPD Difference from Overall Mean",
    x = "Date",
    y = "VPD Difference (kPa)",
    color = "Vegetation"
  )

ggplot(veg_mean_ref_vpd, aes(x = Date, y = cum_diff, color = vegetation)) +
  geom_line(linewidth = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Willow" = "#C99800",
    "Herbaceous" = "#2E8B57",
    "Sedge" = "#2C7FB8"
  )) +
  theme_minimal() +
  labs(
    title = "Cumulative VPD Difference from Overall Mean",
    x = "Date",
    y = "Cumulative Difference (kPa)",
    color = "Vegetation"
  )
# ---------------------------------------------------------
# PLOT 3: VPD difference by geomorph (reference = Riparian)
# Shows the daily VPD difference between Riparian and each
# of the other geomorphic positions (Terrace, Fan), plus the
# cumulative sum of those differences. Positive values indicate
# Riparian VPD was higher than the comparison position on that
# day. 
# ---------------------------------------------------------
geom_wide_vpd <- geomorph_daily %>%
  select(Date, geomorph, mean_VPD) %>%
  pivot_wider(names_from = geomorph, values_from = mean_VPD)

geom_wide_vpd <- geom_wide_vpd %>%
  mutate(
    diff_Riparian_Terrace = Riparian - Terrace,
    diff_Riparian_Fan = Riparian - Fan
  )

geom_diff_long_vpd <- geom_wide_vpd %>%
  select(Date, diff_Riparian_Terrace, diff_Riparian_Fan) %>%
  pivot_longer(
    cols = starts_with("diff"),
    names_to = "comparison",
    values_to = "diff_value"
  )

ggplot(geom_diff_long_vpd, aes(x = Date, y = diff_value, color = comparison)) +
  geom_line(linewidth = 1) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "diff_Riparian_Terrace" = "#D95F02",
    "diff_Riparian_Fan" = "#7570B3"
  )) +
  theme_minimal() +
  labs(
    title = "Daily VPD Difference from Riparian",
    x = "Date",
    y = "VPD Difference (kPa)",
    color = "Comparison"
  )

geom_cum_diff_vpd <- geom_wide_vpd %>%
  arrange(Date) %>%
  mutate(
    cum_diff_Riparian_Terrace = cumsum(ifelse(is.na(diff_Riparian_Terrace), 0, diff_Riparian_Terrace)),
    cum_diff_Riparian_Fan = cumsum(ifelse(is.na(diff_Riparian_Fan), 0, diff_Riparian_Fan))
  )

ggplot(geom_cum_diff_vpd, aes(x = Date)) +
  geom_line(aes(y = cum_diff_Riparian_Terrace, color = "Terrace"), linewidth = 1.2) +
  geom_line(aes(y = cum_diff_Riparian_Fan, color = "Fan"), linewidth = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Terrace" = "#D95F02",
    "Fan" = "#7570B3"
  )) +
  theme_minimal() +
  labs(
    title = "Cumulative VPD Difference from Riparian",
    x = "Date",
    y = "Cumulative Difference (kPa)",
    color = "Geomorph"
  )

# ---------------------------------------------------------
# PLOT 4: VPD difference by geomorph (reference = Mean)
# Same logic as the vegetation mean-reference plots above,
# but applied to geomorphic positions. Shows each position's
# daily VPD departure from the cross-geomorph mean, plus the
# cumulative version. 
# ---------------------------------------------------------
geom_mean_all_vpd <- geomorph_daily %>%
  group_by(Date) %>%
  summarise(
    overall_mean = mean(mean_VPD, na.rm = TRUE),
    .groups = "drop"
  )

geom_mean_ref_vpd <- geomorph_daily %>%
  left_join(geom_mean_all_vpd, by = "Date") %>%
  mutate(
    diff_from_mean = mean_VPD - overall_mean
  ) %>%
  arrange(geomorph, Date) %>%
  group_by(geomorph) %>%
  mutate(
    cum_diff = cumsum(ifelse(is.na(diff_from_mean), 0, diff_from_mean))
  ) %>%
  ungroup()
ggplot(geom_mean_ref_vpd, aes(x = Date, y = diff_from_mean, color = geomorph)) +
  geom_line(linewidth = 1.1) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Riparian" = "#1B9E77",
    "Terrace" = "#D95F02",
    "Fan" = "#7570B3"
  )) +
  theme_minimal() +
  labs(
    title = "Daily VPD Difference from Overall Mean (Geomorph)",
    x = "Date",
    y = "VPD Difference (kPa)",
    color = "Geomorph"
  )
ggplot(geom_mean_ref_vpd, aes(x = Date, y = cum_diff, color = geomorph)) +
  geom_line(linewidth = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  scale_color_manual(values = c(
    "Riparian" = "#1B9E77",
    "Terrace" = "#D95F02",
    "Fan" = "#7570B3"
  )) +
  theme_minimal() +
  labs(
    title = "Cumulative VPD Difference from Overall Mean (Geomorph)",
    x = "Date",
    y = "Cumulative Difference (kPa)",
    color = "Geomorph"
  )


# =========================================================
# PART 2 — DISCRETE LEAF TEMPERATURE MEASUREMENTS
# =========================================================

canopy <- read_csv("Desktop/canopy_temp_CORRECTED.csv") %>%
  mutate(Date = as.Date(Date)) %>%
  select(well_id, Date, Temp_canopy_C)

head(canopy)

leaf_join <- daily_well %>%
  inner_join(canopy, by = c("well_id", "Date")) %>%
  mutate(
    RH_air  = RHave, #from hyro data
    T_air   = Tave, #from hyro data
    T_leaf  = Temp_canopy_C, #from leaf temp measurement 
    VPD_air = RHtoVPD(RH_air, T_air), 
    RH_leaf = RHairToLeaf(RH_air, T_air, T_leaf),
    VPD_leaf_1 = RHtoVPD(RH_air, T_leaf), #leaf temp + air RH 
    VPD_leaf_2 = VPDairToLeaf(VPD_air, T_air, T_leaf), #this uses leaf temp + leaf RH, the air to leaf RH function is already biult in in VPD conversion 
  )
head(leaf_join)
# ---------------------------------------------------------
# PLOT 1: Hygro temp vs leaf temp
# Compares the daily air temperature recorded by the hygrochron
# logger (blue) with the discrete canopy surface temperature
# measured with an IR thermometer (orange), faceted by well.
# ---------------------------------------------------------
temp_df <- leaf_join %>%
  select(Date, well_id, T_air, T_leaf) %>%
  pivot_longer(
    cols = c(T_air, T_leaf),
    names_to = "Temp_type",
    values_to = "Temperature"
  ) %>%
  mutate(
    Temp_type = recode(
      Temp_type,
      "T_air" = "Hygrochron temp",
      "T_leaf" = "Leaf temp"
    )
  ) %>%
  filter(!is.na(Temperature), Temperature < 50)

ggplot(temp_df, aes(x = Date, y = Temperature, color = Temp_type)) +
  geom_point(size = 2, alpha = 0.8) +
  facet_wrap(~ well_id, ncol = 4) +
  scale_color_manual(values = c(
    "Hygrochron temp" = "#2C7FB8",
    "Leaf temp" = "#D95F0E"
  )) +
  theme_minimal() +
  labs(
    title = "Temperature Comparison by Well",
    x = "Date",
    y = "Temperature (°C)",
    color = NULL
  ) +
  theme(
    legend.position = "top",
    axis.text.x = element_text(angle = 45, hjust = 1),
    strip.text = element_text(face = "bold")
  )
# ---------------------------------------------------------
# PLOT 2: Hygro temp vs leaf RH
# Compares the air relative humidity from the hygrochron (blue)
# with the relative humidity converted to the leaf surface
# (orange) using the plantecophys RHairToLeaf function,
# faceted by well.
# ---------------------------------------------------------
RH_df <- leaf_join %>%
  select(Date, well_id, RH_air, RH_leaf) %>%
  pivot_longer(
    cols = c(RH_air, RH_leaf),
    names_to = "RH_type",
    values_to = "Relative_Humidity"
  ) %>%
  mutate(
    RH_type = recode(
      RH_type,
      "RH_air" = "Air RH",
      "RH_leaf" = "R package Converted Leaf RH"
    )
  )

ggplot(RH_df, aes(x = Date, y = Relative_Humidity, color = RH_type)) +
  geom_point(size = 2, alpha = 0.8) +
  facet_wrap(~ well_id, ncol = 4) +
  scale_color_manual(values = c(
    "Air RH" = "#2C7FB8",
    "R package Converted Leaf RH" = "#D95F0E"
  )) +
  theme_minimal() +
  labs(
    title = "RH Comparison by Well",
    x = "Date",
    y = "Relative Humidity (%)",
    color = NULL
  ) +
  theme(
    legend.position = "top",
    axis.text.x = element_text(angle = 45, hjust = 1),
    strip.text = element_text(face = "bold")
  )
# ---------------------------------------------------------
# PLOT 3: Air VPD vs leaf-based VPD (with different calculation methods)
# Compares three VPD estimates at each well over time:
#   (blue)   VPD_air   — standard air-based VPD from hygrochron T & RH
#   (red)    VPD_leaf_1 — leaf-temp VPD using air RH (RHtoVPD with T_leaf)
#   (green)  VPD_leaf_2 — leaf-temp VPD using leaf-surface RH
#                         (VPDairToLeaf, which internally converts RH)
# Faceted by well. 
# ---------------------------------------------------------
vpd_df <- leaf_join %>%
  select(Date, well_id, VPD_air, VPD_leaf_1, VPD_leaf_2) %>%
  pivot_longer(
    cols = c(VPD_air, VPD_leaf_1, VPD_leaf_2),
    names_to = "VPD_type",
    values_to = "VPD"
  ) %>%
  mutate(
    VPD_type = recode(
      VPD_type,
      
      "VPD_air" = "Air-based VPD",
      "VPD_leaf_1" = "Leaf-based VPD with air RH",
      "VPD_leaf_2"= "Leaf-based VPD with leaf RH",
    )
  ) %>%
  filter(!is.na(VPD), VPD < 10)

ggplot(vpd_df, aes(x = Date, y = VPD, color = VPD_type)) +
  geom_point(size = 2, alpha = 0.8) +
  facet_wrap(~ well_id, ncol = 4) +
  scale_color_manual(values = c(
    "Air-based VPD" = "#2C7FB8",
    "Leaf-based VPD with air RH" = "#E31A1C",
    "Leaf-based VPD with leaf RH" = "#33A02C"
  )) +
  theme_minimal() +
  labs(
    title = "VPD Comparison by Well",
    x = "Date",
    y = "VPD (kPa)",
    color = NULL
  ) +
  theme(
    legend.position = "top",
    axis.text.x = element_text(angle = 45, hjust = 1),
    strip.text = element_text(face = "bold")
  )

# ---------------------------------------------------------
# PLOT 4: Overall air vs leaf-based VPD
# Same three VPD estimates as Plot 3 but collapsed across all
# wells into a single panel 
# ---------------------------------------------------------
ggplot(vpd_df, aes(x = Date, y = VPD, color = VPD_type)) +
  geom_point(size = 2.2, alpha = 0.75,
             position = position_jitter(width = 0.15, height = 0)) +
  scale_color_manual(values = c(
    "Air-based VPD" = "#2C7FB8",
    "Leaf-based VPD with air RH" = "#E31A1C",
    "Leaf-based VPD with leaf RH" = "#33A02C"
  )) +
  theme_minimal(base_size = 14) +
  labs(
    title = "Overall VPD Comparison",
    x = "Date",
    y = "VPD (kPa)",
    color = NULL
  ) +
  theme(
    legend.position = "right",
    panel.grid.minor = element_blank(),
    axis.text.x = element_text(angle = 45, hjust = 1),
    plot.title = element_text(face = "bold")
  )

# =========================================================
# TABLE 1 — LEAF + AIR COMBINED DATA
# One row per well per measurement date. Pairs hygrochron-
# derived air conditions (T_air, RH_air, VPD_air) with the
# discrete leaf temperature (T_leaf), the converted leaf-
# surface RH (RH_leaf), and two leaf-level VPD estimates
# (VPD_leaf_1: leaf temp + air RH; VPD_leaf_2: leaf temp +
# leaf RH). Also includes site, geomorph, and vegetation
# classification columns for grouping in analysis.
# =========================================================

leaf_join <- leaf_join %>%
  mutate(
    vegetation = case_when(
      substr(well_id, 2, 2) == "W" ~ "Willow",
      substr(well_id, 2, 2) == "H" ~ "Herbaceous",
      substr(well_id, 2, 2) == "E" ~ "Sedge",
      TRUE ~ NA_character_
    ),
    site = case_when(
      substr(well_id, 1, 1) == "E" ~ "East",
      substr(well_id, 1, 1) == "K" ~ "Kiln",
      TRUE ~ NA_character_
    ),
    geomorph = case_when(
      substr(well_id, 3, 3) == "R" ~ "Riparian",
      substr(well_id, 3, 3) == "T" ~ "Terrace",
      substr(well_id, 3, 3) == "F" ~ "Fan",
      TRUE ~ NA_character_
    )
  )
head(leaf_join)
table_leaf <- leaf_join %>%
  select(
    Date,
    well_id,
    
    # Air conditions
    T_air,
    RH_air,
    VPD_air,
    
    # Leaf measurements
    T_leaf,
    RH_leaf,
    
    # Leaf VPD methods
    VPD_leaf_1,   # leaf temp + air RH
    VPD_leaf_2,   # leaf temp + leaf RH
    site, 
    geomorph,
    vegetation
  ) %>%
  arrange(Date, well_id)

head(table_leaf)



# =========================================================
# PART 3 — VPD vs LAI 
# =========================================================
lai_raw <- read_csv("Desktop/LAI_2025_Corrected.csv") %>%
  rename(
    well_id = Well_ID,
    lai_full = LAI_fullcorr,
    lai_half = LAI_halfcorr
  ) %>%
  mutate(
    datetime = mdy_hm(`Date and Time`),
    Date = as.Date(datetime)
  )
head(lai_raw)

lai_daily <- lai_raw %>%
  mutate(
    LAI = lai_full
  ) %>%
  select(Date, well_id, LAI)
head(lai_daily)
tail(lai_daily)
print(n=140, lai_daily)

install.packages("patchwork")
library(patchwork)

lai_daily <- lai_daily %>%
  mutate(
    vegetation = case_when(
      substr(well_id, 2, 2) == "W" ~ "Willow",
      substr(well_id, 2, 2) == "H" ~ "Herbaceous",
      substr(well_id, 2, 2) == "E" ~ "Sedge",
      TRUE ~ NA_character_
    ),
    site = case_when(
      substr(well_id, 1, 1) == "E" ~ "East",
      substr(well_id, 1, 1) == "K" ~ "Kiln",
      TRUE ~ NA_character_
    ),
    geomorph = case_when(
      substr(well_id, 3, 3) == "R" ~ "Riparian",
      substr(well_id, 3, 3) == "T" ~ "Terrace",
      substr(well_id, 3, 3) == "F" ~ "Fan",
      TRUE ~ NA_character_
    )
  )
print(n=140, lai_daily)
# -----------------------------
# join daily hygro + canopy + LAI
# -----------------------------
# 1) for each LAI observation, find closest canopy date in same well
lai_canopy_match <- lai_daily %>%
  rename(Date_lai = Date) %>%
  inner_join(
    canopy %>% rename(Date_canopy = Date),
    by = "well_id"
  ) %>%
  mutate(date_diff = abs(as.numeric(Date_canopy - Date_lai))) %>%
  group_by(well_id, Date_lai) %>%
  slice_min(order_by = date_diff, n = 1, with_ties = FALSE) %>%
  ungroup()

print(n=140, lai_canopy_match)
# check how far apart the matched dates are
lai_canopy_match %>%
  count(date_diff)
head(lai_canopy_match)
head(daily_well)

leaf_join2 <- lai_canopy_match %>%
  left_join(
    daily_well %>%
      select(Date, well_id, Tave, RHave, VPD),
    by = c("well_id", "Date_canopy" = "Date")
  ) %>%
  mutate(
    Date = Date_lai,
    T_air = Tave,
    RH_air = RHave,
    T_leaf = Temp_canopy_C,
    VPD_air = VPD,
    RH_leaf = RHairToLeaf(RH_air, T_air, T_leaf),
    VPD_leaf = VPDairToLeaf(VPD_air, T_air, T_leaf)
  ) %>%
  filter(date_diff <= 3) %>%
  select(
    Date,
    well_id,
    LAI,
    Date_canopy,
    date_diff,
    T_air,
    RH_air,
    VPD_air,
    T_leaf,
    RH_leaf,
    VPD_leaf,
    vegetation,
    site,
    geomorph
  )
print(n=140, leaf_join2)

leaf_join_plot <- leaf_join2 %>%
  filter(
    !is.na(Date),
    !is.na(well_id),
    !is.na(vegetation),
    !is.na(geomorph),
    !is.na(LAI),
    !is.na(T_air),
    !is.na(T_leaf),
    !is.na(VPD_air),
    !is.na(VPD_leaf),
    date_diff <= 3,
    T_air >= -20,
    T_air <= 60,
    T_leaf >= -20,
    T_leaf <= 60,
    VPD_air >= 0,
    VPD_air <= 10,
    VPD_leaf >= 0,
    VPD_leaf <= 10,
  )
print(n=140, leaf_join_plot)

library(dplyr)
library(tidyr)
library(ggplot2)
library(patchwork)

# colors 
veg_colors <- c(
  "Willow" = "#C99800",
  "Herbaceous" = "#2E8B57",
  "Sedge" = "#2C7FB8"
)

# -------------------------
# VPD
# -------------------------
veg_vpd <- leaf_join_plot %>%
  group_by(Date, vegetation) %>%
  summarise(
    Hygrochron_VPD = mean(VPD_air, na.rm = TRUE),
    Leaf_VPD = mean(VPD_leaf, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_longer(
    cols = c(Hygrochron_VPD, Leaf_VPD),
    names_to = "series",
    values_to = "value"
  ) %>%
  mutate(
    series = recode(
      series,
      Hygrochron_VPD = "Hygrochron VPD",
      Leaf_VPD = "Leaf VPD"
    )
  )

# -------------------------
# TEMP
# -------------------------
veg_temp <- leaf_join_plot %>%
  group_by(Date, vegetation) %>%
  summarise(
    Hygrochron_temp = mean(T_air, na.rm = TRUE),
    Leaf_temp = mean(T_leaf, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_longer(
    cols = c(Hygrochron_temp, Leaf_temp),
    names_to = "series",
    values_to = "value"
  ) %>%
  mutate(
    series = recode(
      series,
      Hygrochron_temp = "Hygrochron temp",
      Leaf_temp = "Leaf temp"
    )
  )

# -------------------------
# LAI
# -------------------------
veg_lai <- leaf_join_plot %>%
  group_by(Date, vegetation) %>%
  summarise(
    LAI = mean(LAI, na.rm = TRUE),
    .groups = "drop"
  )

# -------------------------
# PLOTS
# Three-panel stacked figure grouped by vegetation type, showing:
#   Top:    Mean hygrochron VPD (solid) vs. leaf VPD (dashed) per vegetation
#   Middle: Mean hygrochron temperature (solid) vs. leaf temperature (dashed)
#   Bottom: Mean LAI over time
# -------------------------
p_veg_vpd <- ggplot(
  veg_vpd,
  aes(Date, value, color = vegetation, linetype = series,
      group = interaction(vegetation, series))
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = veg_colors) +
  scale_linetype_manual(values = c("Hygrochron VPD" = "solid", "Leaf VPD" = "dashed")) +
  theme_minimal() +
  labs(title = "Vegetation Mean: VPD", y = "VPD (kPa)", x = NULL)

p_veg_temp <- ggplot(
  veg_temp,
  aes(Date, value, color = vegetation, linetype = series,
      group = interaction(vegetation, series))
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = veg_colors) +
  scale_linetype_manual(values = c("Hygrochron temp" = "solid", "Leaf temp" = "dashed")) +
  theme_minimal() +
  labs(title = "Vegetation Mean: Temperature", y = "Temperature (°C)", x = NULL)

p_veg_lai <- ggplot(
  veg_lai,
  aes(Date, LAI, color = vegetation, group = vegetation)
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = veg_colors) +
  theme_minimal() +
  labs(title = "Vegetation Mean: LAI", y = "LAI", x = "Date")

veg_stacked <- p_veg_vpd / p_veg_temp / p_veg_lai

veg_stacked

geom_colors <- c(
  "Riparian" = "#1B9E77",
  "Terrace"  = "#D95F02",
  "Fan"      = "#7570B3"
)

# -------------------------
# VPD
# -------------------------
geom_vpd <- leaf_join_plot %>%
  group_by(Date, geomorph) %>%
  summarise(
    Hygrochron_VPD = mean(VPD_air, na.rm = TRUE),
    Leaf_VPD = mean(VPD_leaf, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_longer(
    cols = c(Hygrochron_VPD, Leaf_VPD),
    names_to = "series",
    values_to = "value"
  ) %>%
  mutate(
    series = recode(
      series,
      Hygrochron_VPD = "Hygrochron VPD",
      Leaf_VPD = "Leaf VPD"
    )
  )

# -------------------------
# TEMP
# -------------------------
geom_temp <- leaf_join_plot %>%
  group_by(Date, geomorph) %>%
  summarise(
    Hygrochron_temp = mean(T_air, na.rm = TRUE),
    Leaf_temp = mean(T_leaf, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_longer(
    cols = c(Hygrochron_temp, Leaf_temp),
    names_to = "series",
    values_to = "value"
  ) %>%
  mutate(
    series = recode(
      series,
      Hygrochron_temp = "Hygrochron temp",
      Leaf_temp = "Leaf temp"
    )
  )

# -------------------------
# LAI
# -------------------------
geom_lai <- leaf_join_plot %>%
  group_by(Date, geomorph) %>%
  summarise(
    LAI = mean(LAI, na.rm = TRUE),
    .groups = "drop"
  )

# -------------------------
# PLOTS
# Three-panel stacked figure grouped by geomorphic position, showing:
#   Top:    Mean hygrochron VPD (solid) vs. leaf VPD (dashed) per geomorph
#   Middle: Mean hygrochron temperature (solid) vs. leaf temperature (dashed)
#   Bottom: Mean LAI over time
# -------------------------
p_geom_vpd <- ggplot(
  geom_vpd,
  aes(Date, value, color = geomorph, linetype = series,
      group = interaction(geomorph, series))
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = geom_colors) +
  scale_linetype_manual(values = c("Hygrochron VPD" = "solid", "Leaf VPD" = "dashed")) +
  theme_minimal() +
  labs(title = "Geomorph Mean: VPD", y = "VPD (kPa)", x = NULL)

p_geom_temp <- ggplot(
  geom_temp,
  aes(Date, value, color = geomorph, linetype = series,
      group = interaction(geomorph, series))
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = geom_colors) +
  scale_linetype_manual(values = c("Hygrochron temp" = "solid", "Leaf temp" = "dashed")) +
  theme_minimal() +
  labs(title = "Geomorph Mean: Temperature", y = "Temperature (°C)", x = NULL)

p_geom_lai <- ggplot(
  geom_lai,
  aes(Date, LAI, color = geomorph, group = geomorph)
) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_color_manual(values = geom_colors) +
  theme_minimal() +
  labs(title = "Geomorph Mean: LAI", y = "LAI", x = "Date")

geom_stacked <- p_geom_vpd / p_geom_temp / p_geom_lai

geom_stacked


# =========================================================
# PART 3 — Night time vs Day time VPD
# =========================================================
# -----------------------------
# 1) Day vs Night Hygrochron VPD
# -----------------------------
vpd_daynight <- data_clean %>%
  mutate(
    hour = hour(datetime),
    period = case_when(
      hour >= 10 & hour < 14 ~ "Daytime",
      TRUE ~ "Nighttime"
    ),
    VPD_10min = RHtoVPD(RH_pct, temperature_C)
  ) %>%
  group_by(Date, well_id, period) %>%
  summarise(
    VPD_air = mean(VPD_10min, na.rm = TRUE),
    T_air = mean(temperature_C, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  filter(VPD_air <= 10)

# -----------------------------
# 2) KEEP ONLY DAYTIME for leaf calculation
# -----------------------------
vpd_day <- vpd_daynight %>%
  filter(period == "Daytime")

# -----------------------------
# 3) Join canopy (leaf temp)
# -----------------------------
vpd_day_leaf <- vpd_day %>%
  left_join(canopy, by = c("well_id", "Date")) %>%
  mutate(
    T_leaf = Temp_canopy_C,
    VPD_leaf = VPDairToLeaf(VPD_air, T_air, T_leaf)
  ) %>%
  filter(!is.na(VPD_leaf), VPD_leaf <= 10)

# -----------------------------
# PLOT — Daytime vs Nighttime VPD with Leaf VPD overlay (by well)
# For each well, shows:
#   Red lines   — mean VPD during daytime hours (10:00–14:00) from hygrochron, adjust the time if needed
#   Blue lines  — mean VPD during all other hours (nighttime) from hygrochron
#   Green dots  — daytime leaf-level VPD (VPDairToLeaf) on measurement dates
# Faceted by well. 
# -----------------------------
ggplot() +
  
  # --- DAYTIME line
  geom_line(
    data = vpd_daynight,
    aes(
      x = Date,
      y = VPD_air,
      color = period,
      group = interaction(well_id, period)
    ),
    linewidth = 1
  ) +
  
  # --- LEAF VPD dots (DAYTIME ONLY)
  geom_point(
    data = vpd_day_leaf,
    aes(
      x = Date,
      y = VPD_leaf
    ),
    color = "#1A9850",
    size = 2.6,
    alpha = 0.95
  ) +
  
  facet_wrap(~ well_id, ncol = 4) +
  
  scale_color_manual(values = c(
    "Daytime" = "#D73027",
    "Nighttime" = "#4575B4"
  )) +
  
  coord_cartesian(ylim = c(0, 9)) +
  
  theme_minimal() +
  
  labs(
    title = "Daytime vs Nighttime VPD with Leaf VPD Overlay",
    subtitle = "Lines = Hygrochron VPD | Dots = Daytime Leaf VPD",
    x = "Date",
    y = "VPD (kPa)",
    color = "Period"
  ) +
  
  theme(
    legend.position = "top",
    strip.text = element_text(face = "bold"),
    axis.text.x = element_text(angle = 45, hjust = 1)
  )


# =========================================================
# DAY/NIGHT VPD + DAYTIME LEAF VPD (MEAN PER VEGETATION)
# =========================================================

library(dplyr)
library(lubridate)
library(ggplot2)

# -----------------------------
# 1) Day vs Night Hygrochron VPD + vegetation
# -----------------------------
vpd_daynight <- data_clean %>%
  mutate(
    hour = hour(datetime),
    period = case_when(
      hour >= 6 & hour < 18 ~ "Daytime",
      TRUE ~ "Nighttime"
    ),
    vegetation = case_when(
      substr(well_id, 2, 2) == "W" ~ "Willow",
      substr(well_id, 2, 2) == "H" ~ "Herbaceous",
      substr(well_id, 2, 2) == "E" ~ "Sedge",
      TRUE ~ NA_character_
    ),
    VPD_10min = RHtoVPD(RH_pct, temperature_C)
  ) %>%
  group_by(Date, vegetation, period) %>%
  summarise(
    VPD_air = mean(VPD_10min, na.rm = TRUE),
    T_air = mean(temperature_C, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  filter(VPD_air <= 10)

# -----------------------------
# 2) Daytime only → leaf VPD
# -----------------------------
vpd_day_leaf <- vpd_daynight %>%
  filter(period == "Daytime") %>%
  left_join(
    canopy %>%
      mutate(
        vegetation = case_when(
          substr(well_id, 2, 2) == "W" ~ "Willow",
          substr(well_id, 2, 2) == "H" ~ "Herbaceous",
          substr(well_id, 2, 2) == "E" ~ "Sedge",
          TRUE ~ NA_character_
        )
      ) %>%
      group_by(Date, vegetation) %>%
      summarise(
        T_leaf = mean(Temp_canopy_C, na.rm = TRUE),
        .groups = "drop"
      ),
    by = c("Date", "vegetation")
  ) %>%
  mutate(
    VPD_leaf = VPDairToLeaf(VPD_air, T_air, T_leaf)
  ) %>%
  filter(!is.na(VPD_leaf), VPD_leaf <= 10)

# -----------------------------
# PLOT — Vegetation Mean VPD (Day vs Night) with Leaf VPD
# Aggregated version of the per-well day/night plot, collapsed
# to vegetation-type means. Solid lines = daytime hygrochron VPD;
# dashed lines = nighttime hygrochron VPD; dots = daytime leaf VPD.
# All three vegetation types shown on a single panel, colored by type.
# -----------------------------
ggplot() +
  
  # --- Day + Night lines
  geom_line(
    data = vpd_daynight,
    aes(
      x = Date,
      y = VPD_air,
      color = vegetation,
      linetype = period,
      group = interaction(vegetation, period)
    ),
    linewidth = 1.2
  ) +
  
  # --- Daytime leaf VPD dots
  geom_point(
    data = vpd_day_leaf,
    aes(
      x = Date,
      y = VPD_leaf,
      color = vegetation
    ),
    size = 2.8,
    alpha = 0.95
  ) +
  
  scale_color_manual(values = veg_colors) +
  
  scale_linetype_manual(values = c(
    "Daytime" = "solid",
    "Nighttime" = "dashed"
  )) +
  
  coord_cartesian(ylim = c(0, 8)) +
  
  theme_minimal() +
  
  labs(
    title = "Vegetation Mean VPD (Day vs Night) with Leaf VPD",
    subtitle = "Lines = Hygrochron VPD | Dots = Daytime Leaf VPD",
    x = "Date",
    y = "VPD (kPa)",
    color = "Vegetation",
    linetype = "Period"
  ) +
  
  theme(
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )


print(data_clean, n = 200)

# ---------------------------------------------------------
# HOURLY VPD (from 10-min data)
# Aggregates the 10-minute hygrochron readings to hourly means
# per well. Used as the basis for all subsequent daily VPD
# metrics (mean, variance, min/max, and day/night averages).
# ---------------------------------------------------------
hourly_vpd <- data_clean %>%
  mutate(
    datetime_hour = floor_date(datetime, "hour"),
    Date = as.Date(datetime_hour),
    hour = hour(datetime_hour),
    VPD_10min = RHtoVPD(RH_pct, temperature_C)
  ) %>%
  group_by(well_id, Date, hour) %>%
  summarise(
    VPD_hour = mean(VPD_10min, na.rm = TRUE),
    .groups = "drop"
  )
head(hourly_vpd)

# ---------------------------------------------------------
# DAILY VPD METRICS FROM HOURLY
# Summarises hourly VPD into per-well daily statistics:
#   VPD_mean — mean of all hourly VPD values for the day
#   VPD_var  — variance of hourly VPD (proxy for diurnal variability)
#   VPD_min  — minimum hourly VPD and the hour it occurred
#   VPD_max  — maximum hourly VPD and the hour it occurred
# ---------------------------------------------------------
daily_vpd_metrics <- hourly_vpd %>%
  group_by(well_id, Date) %>%
  summarise(
    VPD_mean = mean(VPD_hour, na.rm = TRUE),
    VPD_var  = var(VPD_hour, na.rm = TRUE),
    
    VPD_min = min(VPD_hour, na.rm = TRUE),
    hour_min = hour[which.min(VPD_hour)],
    
    VPD_max = max(VPD_hour, na.rm = TRUE),
    hour_max = hour[which.max(VPD_hour)],
    
    .groups = "drop"
  )

hourly_vpd <- hourly_vpd %>%
  mutate(
    period = case_when(
      hour >= 6 & hour < 18 ~ "Daytime",
      TRUE ~ "Nighttime"
    )
  )

daily_daynight <- hourly_vpd %>%
  group_by(well_id, Date, period) %>%
  summarise(
    VPD_period = mean(VPD_hour, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  pivot_wider(
    names_from = period,
    values_from = VPD_period
  )



# ---------------------------------------------------------
# PLOT — Daily VPD Variance by well (from hourly data)
# Faceted time series of the daily variance in hourly VPD
# for each well. High variance indicates days with a strong
# diurnal VPD cycle (low at night, high during the day).
# ---------------------------------------------------------
ggplot(daily_vpd_metrics, aes(Date, VPD_var)) +
  geom_line(color = "purple", linewidth = 1) +
  facet_wrap(~ well_id, ncol = 4) +
  theme_minimal() +
  labs(
    title = "Daily VPD Variance (from Hourly Data)",
    x = "Date",
    y = "Variance (kPa²)"
  )


# ---------------------------------------------------------
# PLOT — Daily VPD structure: Mean, Day/Night averages, and Range
# For each well (faceted), shows:
#   Grey ribbon — daily min-to-max hourly VPD range
#   Black line  — daily mean VPD
#   Red line    — daytime mean VPD (06:00–18:00)
#   Blue line   — nighttime mean VPD (18:00–06:00)
# ---------------------------------------------------------

plot2_df <- daily_vpd_metrics %>%
  left_join(daily_daynight, by = c("well_id", "Date"))
ggplot(plot2_df, aes(x = Date)) +
  
  # --- shaded min–max range
  geom_ribbon(
    aes(ymin = VPD_min, ymax = VPD_max),
    fill = "grey70",
    alpha = 0.4
  ) +
  
  # --- mean
  geom_line(aes(y = VPD_mean), color = "black", linewidth = 1.2) +
  
  # --- daytime
  geom_line(aes(y = Daytime), color = "#D73027", linewidth = 1) +
  
  # --- nighttime
  geom_line(aes(y = Nighttime), color = "#4575B4", linewidth = 1) +
  
  facet_wrap(~ well_id, ncol = 4) +
  
  theme_minimal() +
  labs(
    title = "Daily VPD Structure (Mean, Day/Night, Range)",
    subtitle = "Ribbon = min–max hourly VPD",
    x = "Date",
    y = "VPD (kPa)"
  )


print(daily_vpd_metrics, n = 2120)
# ---------------------------------------------------------
# PLOT — Hour of daily maximum VPD by well
# Shows which hour of the day the maximum VPD occurred,
# faceted by well. 
# might need to check some oct-nov dates to see why abnormal patterns (super low) happened
# ---------------------------------------------------------
ggplot(daily_vpd_metrics, aes(Date, hour_max)) +
  geom_line(color = "red") +
  facet_wrap(~ well_id) +
  theme_minimal() +
  labs(
    title = "Hour of Daily Maximum VPD",
    y = "Hour of Day"
  )


daily_vpd_metrics <- daily_vpd_metrics %>%
  left_join(
    daily_well %>% select(well_id, vegetation, geomorph) %>% distinct(),
    by = "well_id"
  )

veg_summary <- daily_vpd_metrics %>%
  group_by(Date, vegetation) %>%
  summarise(
    mean_VPD = mean(VPD_mean, na.rm = TRUE),
    min_VPD  = mean(VPD_min, na.rm = TRUE),
    max_VPD  = mean(VPD_max, na.rm = TRUE),
    var_VPD  = mean(VPD_var, na.rm = TRUE),
    .groups = "drop"
  )

veg_colors <- c(
  "Willow" = "#C99800",
  "Herbaceous" = "#2E8B57",
  "Sedge" = "#2C7FB8"
)

# ---------------------------------------------------------
# PLOT — Vegetation Mean VPD with Daily Range (ribbon)
# For each vegetation type, shows the daily mean VPD as a
# solid line, with a shaded ribbon spanning the average
# daily minimum to average daily maximum across wells.
# ---------------------------------------------------------
ggplot(veg_summary, aes(Date, mean_VPD, color = vegetation)) +
  geom_ribbon(
    aes(ymin = min_VPD, ymax = max_VPD, fill = vegetation),
    alpha = 0.2,
    color = NA
  ) +
  geom_line(linewidth = 1.3) +
  scale_color_manual(values = veg_colors) +
  scale_fill_manual(values = veg_colors) +
  theme_minimal() +
  labs(
    title = "Vegetation Mean VPD with Daily Range",
    y = "VPD (kPa)",
    color = "Vegetation",
    fill = "Vegetation"
  )

geom_colors <- c(
  "Riparian" = "#1B9E77",
  "Terrace" = "#D95F02",
  "Fan" = "#7570B3"
)

geom_summary <- daily_vpd_metrics %>%
  group_by(Date, geomorph) %>%
  summarise(
    mean_VPD = mean(VPD_mean, na.rm = TRUE),
    min_VPD  = mean(VPD_min, na.rm = TRUE),
    max_VPD  = mean(VPD_max, na.rm = TRUE),
    var_VPD  = mean(VPD_var, na.rm = TRUE),
    .groups = "drop"
  )

# ---------------------------------------------------------
# PLOT — Geomorph Mean VPD with Daily Range (ribbon)
# Same structure as the vegetation ribbon plot above,
# but stratified by geomorphic position (Riparian, Terrace,
# Fan). Solid lines = daily mean VPD; shaded ribbons =
# average daily min-to-max range. 
# ---------------------------------------------------------
ggplot(geom_summary, aes(Date, mean_VPD, color = geomorph)) +
  geom_ribbon(
    aes(ymin = min_VPD, ymax = max_VPD, fill = geomorph),
    alpha = 0.2,
    color = NA
  ) +
  geom_line(linewidth = 1.3) +
  scale_color_manual(values = geom_colors) +
  scale_fill_manual(values = geom_colors) +
  theme_minimal() +
  labs(
    title = "Geomorph Mean VPD with Daily Range",
    y = "VPD (kPa)",
    color = "Geomorph",
    fill = "Geomorph"
  )



# ---------------------------------------------------------
# PLOT — Mean daily VPD variance by vegetation
# Shows how the average within-day VPD variance (across wells)
# changes over the season for each vegetation type.
# High values indicate days with large swings between
# low nighttime and high daytime VPD. 
# ---------------------------------------------------------
veg_var_summary <- daily_vpd_metrics %>%
  group_by(Date, vegetation) %>%
  summarise(
    mean_VPD_var = mean(VPD_var, na.rm = TRUE),
    .groups = "drop"
  )

ggplot(veg_var_summary, aes(Date, mean_VPD_var, color = vegetation)) +
  geom_line(linewidth = 1.2) +
  scale_color_manual(values = veg_colors) +
  theme_minimal() +
  labs(
    title = "Mean Daily VPD Variance by Vegetation Type",
    x = "Date",
    y = "Mean VPD variance (kPa²)",
    color = "Vegetation"
  )

# ---------------------------------------------------------
# PLOT — Mean daily VPD variance by geomorph
# Same as the vegetation variance plot above but grouped
# by geomorphic position. Reveals whether topographic
# setting (Riparian, Terrace, Fan) drives systematic
# differences in the amplitude of the diurnal VPD cycle
# across the season.
# ---------------------------------------------------------
geom_var_summary <- daily_vpd_metrics %>%
  group_by(Date, geomorph) %>%
  summarise(
    mean_VPD_var = mean(VPD_var, na.rm = TRUE),
    .groups = "drop"
  )

ggplot(geom_var_summary, aes(Date, mean_VPD_var, color = geomorph)) +
  geom_line(linewidth = 1.2) +
  scale_color_manual(values = geom_colors) +
  theme_minimal() +
  labs(
    title = "Mean Daily VPD Variance by Geomorphic Position",
    x = "Date",
    y = "Mean VPD variance (kPa²)",
    color = "Geomorph"
  )

