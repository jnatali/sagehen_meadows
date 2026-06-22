# Load required libraries
#link to the evapotranspiration library 
#https://cran.r-project.org/web/packages/Evapotranspiration/Evapotranspiration.pdf
install.packages("Evapotranspiration")
library(Evapotranspiration)
library(dplyr)
library(lubridate)
library(readr)

#-------------------------------------------------
#step(0): set up and read in data 
file <- "data_wrcc.csv"
#provided by https://wrcc.dri.edu/cgi-bin/rawMAIN.pl?nvsagh
lat_deg <- 39 + 25/60 + 57/3600  
elev_m <- 1931.5176
#the data downloaded from sagehen wrcc marks missing data as one of the following 
missing_codes <- c(99, 999, 9999, -99, -999, -9999)

# Read raw data
raw <- read_csv(file, skip = 3, show_col_types = FALSE)

colnames(raw) <- c(
  "Date", "Time", "Tavg_C_10min", "Tmax_C_10min", "Tmin_C_10min",
  "RH_10min", "RHmax_10min", "RHmin_10min", "Barom_mbar_10min", "Solar_Wm2_10min"
)

#-------------------------------------------------
# Step(1): conversions 
data <- raw
#convert missing data (9999) to NA 
data[data %in% missing_codes] <- NA

# Ensure Date is actually a Date object to avoid format errors
data$Date <- as.Date(data$Date, format="%m/%d/%y")

#Units of the solar radiation in wrcc data is Solar_Wm2_10min, we i think it might mean Watts per square meter
#1 Watt = 1 Joule per second --> W/m^2 = Joules/second/m^2
#since data interval is 10 min so it is 600 seconds 
#The Evapotranspiration package requires solar radiation in Megajoules (MJ), not standard Joules (J).1 Megajoule=1,000,000 Joules (or 10^6)
dt_min <- 10  # data interval in 10 minutes
dt_seconds <- dt_min * 60
data <- data %>% mutate(Rs_interval_MJ = Solar_Wm2_10min * dt_seconds / 1e6)


# Step (2): Define Constants ---
# Priestley-Taylor specifically requires alphaPT and G , I use the same values provided by the package document 
constants <- list(
  Elev    = elev_m,
  lat_rad = lat_deg * pi / 180,
  lambda  = 2.45,       # Latent heat of vaporisation 
  Gsc     = 0.0820,     # Solar constant 
  sigma   = 4.903e-9,   # Stefan-Boltzmann constant 
  alphaPT = 1.26,       # Priestley-Taylor coefficient 
  G       = 0           # Soil heat flux (0 for daily) 
)

# Step (3): Aggregate to daily and format Data for the Package

#summarize into daily data and remove anything that's missing or unreasonable
daily_clean <- data %>%
  group_by(Date) %>%
  summarise(
    Tave  = mean(Tavg_C_10min, na.rm = TRUE),
    Tmax  = max(Tmax_C_10min,  na.rm = TRUE),
    Tmin  = min(Tmin_C_10min,  na.rm = TRUE),
    RHmax = max(RHmax_10min,   na.rm = TRUE),
    RHmin = min(RHmin_10min,   na.rm = TRUE),
    RHave = mean(RH_10min,     na.rm = TRUE),  
    Rs    = sum(Rs_interval_MJ, na.rm = TRUE), 
    
    anyNA = any(is.na(Tavg_C_10min) | is.na(Tmax_C_10min) | 
                  is.na(Tmin_C_10min) | is.na(Solar_Wm2_10min) |
                  is.na(RH_10min)) 
  ) %>%
  filter(
    !anyNA,
    Tave >= -50 & Tave < 60,  
    Tmax >= -50 & Tmax < 60,   
    Tmin >= -50 & Tmin < 60,
    Tmax >= Tmin,            
    RHmax <= 100 & RHmin >= 0,
    RHmax >= RHmin,           
    Rs >= 0 & Rs < 40         
  ) %>%
  mutate(
    Year  = as.numeric(format(Date, "%Y")),
    Month = as.numeric(format(Date, "%m")),
    Day   = as.numeric(format(Date, "%d"))
  )
varnames <- c("Tmax", "Tmin", "RHmax", "RHmin", "Rs")

# --- Step 3.5: Format Data using ReadInputs ---
varnames <- c("Tmax", "Tmin", "RHmax", "RHmin", "Rs")

# --- Step 3.5: Format Data using ReadInputs ---
varnames <- c("Tmax", "Tmin", "RHmax", "RHmin", "Rs")

data_formatted <- ReadInputs(
  varnames = varnames,
  climatedata = daily_clean,
  constants = constants,
  stopmissing = c(10, 10, 10),
  timestep = "daily",
  #interpolation, biult in in the packages 
  interp_missing_days = TRUE, 
  interp_missing_entries = TRUE, # Changed to TRUE to help with interpolation
  interp_abnormal = TRUE,        # Helps clean remaining sensor spikes
  missing_method = "monthly average" # replace any missing/bad data with monthly average 
)
head(data_formatted)
# Step (4): Run Priestley-Taylor ET ---
res <- ET.PriestleyTaylor(
  data = data_formatted,
  constants = constants,
  ts = "daily",
  solar = "data",
  alpha = 0.23,
  message = "yes",
  AdditionalStats = "yes"
)

# 2. Match the dates correctly
# ReadInputs might have added or removed days to fill gaps, 
# so we pull the dates directly from the results object.
out <- data.frame(
  Date = index(res$ET.Daily), 
  ET_mm_day = as.numeric(res$ET.Daily)
)

ETPlot(res, type = "Daily")


library(ggplot2)
ggplot(out, aes(x = Date, y = ET_mm_day)) +
  geom_line(color = "steelblue", linewidth = 0.8) +
  geom_smooth(method = "gam", color = "red", se = FALSE, linetype = "dashed") + # Adds a trend line
  labs(
    title = "Daily Evapotranspiration (Priestley-Taylor Method)",
    subtitle = paste("Location Lat:", round(lat_deg, 2), "Elev:", elev_m, "m"),
    x = "Date",
    y = "ET (mm/day)"
  ) +
  theme_minimal() +
  scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))


#step (4) calculate daily average VPD
head(daily_clean)
install.packages("plantecophys")

library(plantecophys)

# Calculate Daily Average VPD
# Note: RH should be in % and Temp in Celsius
daily_clean <- daily_clean %>%
  mutate(
    VPD = RHtoVPD(RHave, Tave)
  )
summary(daily_clean$RHave)

library(ggplot2)

ggplot(daily_clean, aes(x = Date, y = VPD)) +
  geom_line(color = "darkblue", size = 0.5) +  # The daily data
  geom_smooth(method = "loess", color = "red", se = FALSE) + # The seasonal trend
  labs(title = "Daily Vapor Pressure Deficit (VPD) Time Series",
       subtitle = "Calculated using RHave and Tave",
       x = "Date",
       y = "VPD (kPa)") +
  theme_minimal()

print(head(daily_clean))