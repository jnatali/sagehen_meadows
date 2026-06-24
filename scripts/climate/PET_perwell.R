# Calculates ET via PriestleyTaylor for each well
#step 0
library(tidyverse)
library(lubridate)
library(readr)
#install.packages("Evapotranspiration")
library(Evapotranspiration)
library(dplyr)
#library(lubridate)
#library(readr)

#library(tidyverse)
#library(lubridate)
#library(readr)
#library(Evapotranspiration)
library(here)

# ---------------------------
# STEP 1: READ HYGRO DATA
# ---------------------------
data <- read_csv(here("data", "field_observations", "hygrochron", "hygrochron_2025_10min_per_well.csv")) %>%
  mutate(
    datetime = mdy_hms(datetime),
    Date = as.Date(datetime)
  )

# ---------------------------
# STEP 2: READ WRCC DATA
# ---------------------------
library(readr)
library(dplyr)
library(lubridate)

# wrcc_data <- read_csv(
#   here("data", "station_instrumentation", "climate", "Weather_2010_2025_10min_SagehenTower1.csv"),
#   skip = 3,
#   na = "-999",
#   col_names = c(
#     "Date", "Time",
#     "Tavg_C", "Tmax_C", "Tmin_C",
#     "RH_pct", "RHmax_pct", "RHmin_pct",
#     "Pressure_mbar", "Solar_Wm2",
#     "Precip_mm", "AccumPcpn_mm",
#     "SnowMaxDep_mm", "SnowMinDep_mm", "SnowDepth_mm"
#   ),
#   show_col_types = FALSE
# ) %>%
#   mutate(
#     datetime = mdy_hm(paste(Date, Time)),
#     Date = as.Date(datetime)
#   )

# head(wrcc_data)
# tail(wrcc_data)

wrcc_data <- read_csv(
  here("data",  "station_instrumentation", "climate", "Weather_2010_2025_10min_SagehenTower1.csv"),
  skip = 3,
  na = "-999",
  col_names = c(
    "datetime_raw",  # <-- Replaced "Date" and "Time" with this single column
    "Tavg_C", "Tmax_C", "Tmin_C",
    "RH_pct", "RHmax_pct", "RHmin_pct",
    "Pressure_mbar", "Solar_Wm2",
    "Precip_mm", "AccumPcpn_mm",
    "SnowMaxDep_mm", "SnowMinDep_mm", "SnowDepth_mm"
  ),
  show_col_types = FALSE
) %>%
  mutate(
    # Parse the single column directly. 
    # Your image shows M/D/YY H:MM, so mdy_hm() is the perfect function!
    datetime = mdy_hm(datetime_raw),
    Date = as.Date(datetime),
    # Moving your Solar parsing here just in case it still needs it
    Solar_Wm2 = as.numeric(Solar_Wm2) 
  )

head(wrcc_data)
tail(wrcc_data)
# ---------------------------
# STEP 3: DAILY SUMMARY PER WELL
# ---------------------------
daily_hygro <- data %>%
  group_by(well_id, Date) %>%
  summarise(
    Tmax  = max(temperature_C, na.rm = TRUE),
    Tmin  = min(temperature_C, na.rm = TRUE),
    RHmax = max(RH_pct, na.rm = TRUE),
    RHmin = min(RH_pct, na.rm = TRUE),
    .groups = "drop"
  )

# ---------------------------
# STEP 4: DAILY SOLAR
# ---------------------------
daily_wrcc <- wrcc_data %>%
  mutate(
    #Solar_Wm2 = readr::parse_number(Solar_Wm2),
    Rs_interval_MJ = Solar_Wm2 * 600 / 1e6   # 600 sec = 10 min
  ) %>%
  group_by(Date) %>%
  summarise(
    Rs = sum(Rs_interval_MJ, na.rm = TRUE),
    Precip_mm = sum(Precip_mm, na.rm = TRUE),
    .groups = "drop"
  )
head(daily_wrcc)

# ---------------------------
# STEP 5: MERGE
# ---------------------------
daily_clean <- daily_hygro %>%
  left_join(daily_wrcc, by = "Date") %>%
  arrange(well_id, Date) %>%
  group_by(well_id, Date) %>%
  summarise(
    Tmax = mean(Tmax, na.rm = TRUE),
    Tmin = mean(Tmin, na.rm = TRUE),
    RHmax = mean(RHmax, na.rm = TRUE),
    RHmin = mean(RHmin, na.rm = TRUE),
    Rs = mean(Rs, na.rm = TRUE),
    Precip_mm = mean(Precip_mm, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    Year  = year(Date),
    Month = month(Date),
    Day   = day(Date)
  )
head(daily_clean)

# =========================================================
# CONSTANTS
# =========================================================
lat_deg <- 39 + 25/60 + 57/3600  
elev_m <- 1931.5176

constants <- list(
  Elev    = elev_m,
  lat_rad = lat_deg * pi / 180,
  lambda  = 2.45,
  Gsc     = 0.0820,
  sigma   = 4.903e-9,
  alphaPT = 1.26,
  G       = 0
)

# ---------------------------
# STEP 6: RUN PET PER WELL 
# ---------------------------
wells <- unique(daily_clean$well_id)

results_list <- list()

for (w in wells) {
  
  cat("Running well:", w, "\n")
  
  df_well <- daily_clean %>%
    filter(well_id == w) %>%
    arrange(Date)
  
  # ensure no duplicate dates
  df_well <- df_well %>%
    group_by(Date) %>%
    summarise(
      Tmax = mean(Tmax, na.rm = TRUE),
      Tmin = mean(Tmin, na.rm = TRUE),
      RHmax = mean(RHmax, na.rm = TRUE),
      RHmin = mean(RHmin, na.rm = TRUE),
      Rs = mean(Rs, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    mutate(
      Year  = year(Date),
      Month = month(Date),
      Day   = day(Date)
    )
  
  df_well <- df_well %>%
    arrange(Date) %>%
    slice(3:(n() - 2))
  
  # format for ET package
  data_formatted <- ReadInputs(
    varnames = c("Tmax", "Tmin", "RHmax", "RHmin", "Rs"),
    climatedata = df_well,
    constants = constants,
    stopmissing = c(10, 10, 10),
    timestep = "daily"
  )
  
  # run PET (UNCHANGED alpha)
  res <- ET.PriestleyTaylor(
    data = data_formatted,
    constants = constants,
    ts = "daily",
    solar = "data",
    alpha = 0.23,
    message = "yes"
  )
  
  # store results
  results_list[[w]] <- data.frame(
    Date = df_well$Date,
    well_id = w,
    PET_mm_day = res$ET.Daily
  )
}

# ---------------------------
# STEP 7: COMBINE RESULTS
# ---------------------------
pet_by_well <- do.call(rbind, results_list)

# check
head(pet_by_well)

# ---------------------------
# STEP 8: ADD GROUP VARIABLES
# ---------------------------
pet_by_well <- pet_by_well %>%
  left_join(
    daily_clean %>% select(Date, well_id, Precip_mm),
    by = c("Date", "well_id")
  ) %>%
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

pet_by_well <- pet_by_well %>%
  mutate(
    vegetation = factor(vegetation,
                        levels = c("Willow", "Herbaceous", "Sedge"))
  )

# =========================================================
# EXPORT DATA FOR PYTHON
# =========================================================
write_csv(pet_by_well, here("data", "field_observations", "pet_by_well_results.csv"))

cat("Export complete! Saved to Desktop/pet_by_well_results.csv\n")
# # =========================================================
# # STEP 9: SUMMARIES
# # =========================================================

# # overall
# overall_daily <- pet_by_well %>%
#   group_by(Date) %>%
#   summarise(
#     mean_PET = mean(PET_mm_day, na.rm = TRUE),
#     Precip_mm = mean(Precip_mm, na.rm = TRUE),
#     .groups = "drop"
#   ) %>%
#   arrange(Date)

# # vegetation
# veg_mean_pet <- pet_by_well %>%
#   group_by(Date, vegetation) %>%
#   summarise(
#     mean_PET = mean(PET_mm_day, na.rm = TRUE),
#     Precip_mm = mean(Precip_mm, na.rm = TRUE),
#     .groups = "drop"
#   ) %>%
#   arrange(vegetation, Date) %>%
#   group_by(vegetation) %>%
#   mutate(
#     cum_PET = cumsum(mean_PET)
#   ) %>%
#   ungroup()

# veg_cum_precip <- overall_daily %>%
#   mutate(cum_Precip = cumsum(Precip_mm)) %>%
#   select(Date, cum_Precip)

# # geomorph
# geom_mean_pet <- pet_by_well %>%
#   group_by(Date, geomorph) %>%
#   summarise(
#     mean_PET = mean(PET_mm_day, na.rm = TRUE),
#     Precip_mm = mean(Precip_mm, na.rm = TRUE),
#     .groups = "drop"
#   ) %>%
#   arrange(geomorph, Date) %>%
#   group_by(geomorph) %>%
#   mutate(
#     cum_PET = cumsum(mean_PET)
#   ) %>%
#   ungroup()

# geom_cum_precip <- overall_daily %>%
#   mutate(cum_Precip = cumsum(Precip_mm)) %>%
#   select(Date, cum_Precip)

# # =========================================================
# # STEP 9: OVERALL PLOT
# # one overall plot all time series + daily precipitation
# # =========================================================
# ggplot() +
#   geom_col(
#     data = overall_daily,
#     aes(x = Date, y = Precip_mm),
#     fill = "grey70",
#     alpha = 0.6
#   ) +
#   geom_line(
#     data = pet_by_well,
#     aes(x = Date, y = PET_mm_day, group = well_id, color = vegetation),
#     linewidth = 0.7,
#     alpha = 0.65
#   ) +
#   scale_color_manual(values = c(
#     "Willow" = "#C99800",
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Daily PET Across All Wells with Daily Precipitation",
#     x = "Date",
#     y = "unit = mm",
#     color = "Vegetation"
#   )

# # =========================================================
# # STEP 10: VEGETATION PLOTS
# # one mean plot + precip
# # one cumulative plot + cumulative precip
# # =========================================================
# ggplot() +
#   geom_col(
#     data = overall_daily,
#     aes(x = Date, y = Precip_mm),
#     fill = "grey70",
#     alpha = 0.6
#   ) +
#   geom_line(
#     data = veg_mean_pet,
#     aes(x = Date, y = mean_PET, color = vegetation),
#     linewidth = 1.2
#   ) +
#   scale_color_manual(values = c(
#     "Willow" = "#C99800",
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Mean Daily PET by Vegetation with Daily Precipitation",
#     x = "Date",
#     y = "unit = mm",
#     color = "Vegetation"
#   )

# ggplot() +
#   geom_line(
#     data = veg_cum_precip,
#     aes(x = Date, y = cum_Precip),
#     color = "grey50",
#     linewidth = 1,
#     linetype = "dashed"
#   ) +
#   geom_line(
#     data = veg_mean_pet,
#     aes(x = Date, y = cum_PET, color = vegetation),
#     linewidth = 1.2
#   ) +
#   scale_color_manual(values = c(
#     "Willow" = "#C99800",
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET by Vegetation with Cumulative Precipitation",
#     x = "Date",
#     y = "Cumulative Value (mm)",
#     color = "Vegetation"
#   )

# # =========================================================
# # STEP 11: GEOMORPH PLOTS
# # one mean plot + precip
# # one cumulative plot + cumulative precip
# # =========================================================
# ggplot() +
#   geom_col(
#     data = overall_daily,
#     aes(x = Date, y = Precip_mm),
#     fill = "grey70",
#     alpha = 0.6
#   ) +
#   geom_line(
#     data = geom_mean_pet,
#     aes(x = Date, y = mean_PET, color = geomorph),
#     linewidth = 1.2
#   ) +
#   scale_color_manual(values = c(
#     "Riparian" = "#1B9E77",
#     "Terrace" = "#D95F02",
#     "Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Mean Daily PET by Geomorph with Daily Precipitation",
#     x = "Date",
#     y = "unit = mm",
#     color = "Geomorph"
#   )

# ggplot() +
#   geom_line(
#     data = geom_cum_precip,
#     aes(x = Date, y = cum_Precip),
#     color = "grey50",
#     linewidth = 1,
#     linetype = "dashed"
#   ) +
#   geom_line(
#     data = geom_mean_pet,
#     aes(x = Date, y = cum_PET, color = geomorph),
#     linewidth = 1.2
#   ) +
#   scale_color_manual(values = c(
#     "Riparian" = "#1B9E77",
#     "Terrace" = "#D95F02",
#     "Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET by Geomorph with Cumulative Precipitation",
#     x = "Date",
#     y = "Cumulative Value (mm)",
#     color = "Geomorph"
#   )

# # =========================================================
# # STEP 12: VEGETATION DIFFERENCE PLOTS
# # reference = Willow
# # one daily difference plot
# # one cumulative difference plot
# # =========================================================
# veg_wide <- veg_mean_pet %>%
#   select(Date, vegetation, mean_PET) %>%
#   tidyr::pivot_wider(names_from = vegetation, values_from = mean_PET)

# print(names(veg_wide))
# print(summary(veg_wide))

# veg_wide <- veg_wide %>%
#   mutate(
#     diff_Willow_Herbaceous = Willow - Herbaceous,
#     diff_Willow_Sedge = Willow - Sedge
#   )

# veg_diff_long <- veg_wide %>%
#   select(Date, diff_Willow_Herbaceous, diff_Willow_Sedge) %>%
#   pivot_longer(
#     cols = starts_with("diff"),
#     names_to = "comparison",
#     values_to = "diff_value"
#   )

# ggplot(veg_diff_long, aes(x = Date, y = diff_value, color = comparison)) +
#   geom_line(linewidth = 1) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "diff_Willow_Herbaceous" = "#2E8B57",
#     "diff_Willow_Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Daily PET Difference from Willow",
#     x = "Date",
#     y = "PET Difference (mm/day)",
#     color = "Comparison"
#   )

# veg_cum_diff <- veg_wide %>%
#   arrange(Date) %>%
#   mutate(
#     cum_diff_Willow_Herbaceous = cumsum(ifelse(is.na(diff_Willow_Herbaceous), 0, diff_Willow_Herbaceous)),
#     cum_diff_Willow_Sedge = cumsum(ifelse(is.na(diff_Willow_Sedge), 0, diff_Willow_Sedge))
#   )

# ggplot(veg_cum_diff, aes(x = Date)) +
#   geom_line(aes(y = cum_diff_Willow_Herbaceous, color = "Herbaceous"), linewidth = 1.2) +
#   geom_line(aes(y = cum_diff_Willow_Sedge, color = "Sedge"), linewidth = 1.2) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET Difference from Willow",
#     x = "Date",
#     y = "Cumulative Difference (mm)",
#     color = "Vegetation"
#   )

# # =========================================================
# # STEP 13: VEGETATION DIFFERENCE FROM OVERALL MEAN
# # daily + cumulative
# # =========================================================
# veg_mean_all <- veg_mean_pet %>%
#   group_by(Date) %>%
#   summarise(
#     overall_mean = mean(mean_PET, na.rm = TRUE),
#     .groups = "drop"
#   )

# veg_mean_ref <- veg_mean_pet %>%
#   left_join(veg_mean_all, by = "Date") %>%
#   mutate(
#     diff_from_mean = mean_PET - overall_mean
#   ) %>%
#   arrange(vegetation, Date) %>%
#   group_by(vegetation) %>%
#   mutate(
#     cum_diff = cumsum(ifelse(is.na(diff_from_mean), 0, diff_from_mean))
#   ) %>%
#   ungroup()

# ggplot(veg_mean_ref, aes(x = Date, y = diff_from_mean, color = vegetation)) +
#   geom_line(linewidth = 1.1) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Willow" = "#C99800",
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Daily PET Difference from Overall Mean (Vegetation)",
#     x = "Date",
#     y = "PET Difference (mm/day)",
#     color = "Vegetation"
#   )

# ggplot(veg_mean_ref, aes(x = Date, y = cum_diff, color = vegetation)) +
#   geom_line(linewidth = 1.2) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Willow" = "#C99800",
#     "Herbaceous" = "#2E8B57",
#     "Sedge" = "#2C7FB8"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET Difference from Overall Mean (Vegetation)",
#     x = "Date",
#     y = "Cumulative Difference (mm)",
#     color = "Vegetation"
#   )

# # =========================================================
# # STEP 14: GEOMORPH DIFFERENCE PLOTS
# # reference = Riparian
# # one daily difference plot
# # one cumulative difference plot
# # =========================================================
# geom_wide <- geom_mean_pet %>%
#   select(Date, geomorph, mean_PET) %>%
#   tidyr::pivot_wider(names_from = geomorph, values_from = mean_PET)

# print(names(geom_wide))
# print(summary(geom_wide))

# geom_wide <- geom_wide %>%
#   mutate(
#     diff_Riparian_Terrace = Riparian - Terrace,
#     diff_Riparian_Fan = Riparian - Fan
#   )

# geom_diff_long <- geom_wide %>%
#   select(Date, diff_Riparian_Terrace, diff_Riparian_Fan) %>%
#   pivot_longer(
#     cols = starts_with("diff"),
#     names_to = "comparison",
#     values_to = "diff_value"
#   )

# ggplot(geom_diff_long, aes(x = Date, y = diff_value, color = comparison)) +
#   geom_line(linewidth = 1) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "diff_Riparian_Terrace" = "#D95F02",
#     "diff_Riparian_Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Daily PET Difference from Riparian",
#     x = "Date",
#     y = "PET Difference (mm/day)",
#     color = "Comparison"
#   )

# geom_cum_diff <- geom_wide %>%
#   arrange(Date) %>%
#   mutate(
#     cum_diff_Riparian_Terrace = cumsum(ifelse(is.na(diff_Riparian_Terrace), 0, diff_Riparian_Terrace)),
#     cum_diff_Riparian_Fan = cumsum(ifelse(is.na(diff_Riparian_Fan), 0, diff_Riparian_Fan))
#   )

# ggplot(geom_cum_diff, aes(x = Date)) +
#   geom_line(aes(y = cum_diff_Riparian_Terrace, color = "Terrace"), linewidth = 1.2) +
#   geom_line(aes(y = cum_diff_Riparian_Fan, color = "Fan"), linewidth = 1.2) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Terrace" = "#D95F02",
#     "Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET Difference from Riparian",
#     x = "Date",
#     y = "Cumulative Difference (mm)",
#     color = "Geomorph"
#   )

# # =========================================================
# # STEP 15: GEOMORPH DIFFERENCE FROM OVERALL MEAN
# # daily + cumulative
# # =========================================================
# geom_mean_all <- geom_mean_pet %>%
#   group_by(Date) %>%
#   summarise(
#     overall_mean = mean(mean_PET, na.rm = TRUE),
#     .groups = "drop"
#   )

# geom_mean_ref <- geom_mean_pet %>%
#   left_join(geom_mean_all, by = "Date") %>%
#   mutate(
#     diff_from_mean = mean_PET - overall_mean
#   ) %>%
#   arrange(geomorph, Date) %>%
#   group_by(geomorph) %>%
#   mutate(
#     cum_diff = cumsum(ifelse(is.na(diff_from_mean), 0, diff_from_mean))
#   ) %>%
#   ungroup()

# ggplot(geom_mean_ref, aes(x = Date, y = diff_from_mean, color = geomorph)) +
#   geom_line(linewidth = 1.1) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Riparian" = "#1B9E77",
#     "Terrace" = "#D95F02",
#     "Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Daily PET Difference from Overall Mean (Geomorph)",
#     x = "Date",
#     y = "PET Difference (mm/day)",
#     color = "Geomorph"
#   )

# ggplot(geom_mean_ref, aes(x = Date, y = cum_diff, color = geomorph)) +
#   geom_line(linewidth = 1.2) +
#   geom_hline(yintercept = 0, linetype = "dashed") +
#   scale_color_manual(values = c(
#     "Riparian" = "#1B9E77",
#     "Terrace" = "#D95F02",
#     "Fan" = "#7570B3"
#   )) +
#   theme_minimal() +
#   labs(
#     title = "Cumulative PET Difference from Overall Mean (Geomorph)",
#     x = "Date",
#     y = "Cumulative Difference (mm)",
#     color = "Geomorph"
#   )





