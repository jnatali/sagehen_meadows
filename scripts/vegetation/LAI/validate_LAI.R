#---------------------------------------------------------
#Step(0): Set-up
library(dplyr)
library(tidyr)
library(ggplot2)
library(lubridate)
library(tibble)


# ------ INITIALIZE GLOBAL VARIABLES ------
# Setup directories and filepaths
home_dir='/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/'
repository_name = 'sagehen_meadows'
repository_dir = paste(home_dir, repository_name, '/', sep='')

LAI_data_dir = 'data/field_observations/vegetation/LAI/'
LAI_results_dir = 'results/vegetation/LAI/'
LAI_plots_dir = 'results/plots/vegetation/'
LAI_corrected_filename = 'LAI_2025_Corrected.csv'
#LAI_results_dir = paste(home_dir, repository_name, '/results/vegetation/LAI/', sep='')
LAI_corrected_file = paste(repository_dir, LAI_data_dir,
                           LAI_corrected_filename,
                           sep='')

data <- read_csv(LAI_corrected_file)

#---------------------------------------------------------
#PART(1): Plotting for Willow LAI

#---------------------------------------------------------
#Step(1): Data preparation
#

data <- data %>%
  mutate(
    is_willow = substr(data$well_id, 2, 2) == "W",
    is_herbaceous = substr(data$well_id, 2, 2) == "H",
    is_sedge = substr(data$well_id, 2, 2) == "E"
  )
data <- data %>%
  mutate(
    is_east = substr(data$well_id, 1, 1) == "E",
    is_kiln = substr(data$well_id, 1, 1) == "K",
  )
data <- data %>%
  mutate(
    is_riparian = substr(data$well_id, 3, 3) == "R",
    is_terrace = substr(data$well_id, 3, 3) == "T",
    is_fan = substr(data$well_id, 3, 3) == "F"
  )

data <- data %>%
  mutate(
    Date = as.Date(data$datetime, format = "%m/%d/%y %H:%M")
  )

data_corrected <- data

#(i): Import data frame for willow
#(ii): Change the data frame from wide - long, format for ggplot

df_willow_long <- data_corrected %>%
  filter(is_willow) %>%
  #(ii)
  pivot_longer(
    cols = c(LAI.sensor, LAI.rmWAI, LAI.halfWAI),
    names_to = "data_type",
    values_to = "value"
  )

#---------------------------------------------------------
#Step(2): Calculate mean across wells per Date + data type
df_willow_mean <- df_willow_long %>%
  group_by(Date, data_type) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop")

#---------------------------------------------------------
#Step(3): plot
w_plot <- ggplot(df_willow_long, aes(x = Date, y = value)) +
  geom_line(aes(group = well_id, color = well_id), alpha = 0.6) +
  geom_line(
    data = df_willow_mean,
    aes(x = Date, y = mean_value, group = 1),
    color = "black",
    linewidth = 1.2
  ) +
  facet_wrap(~ data_type, ncol = 1, scales = "free_y") +
  labs(
    title = "Willow: LAI Correction Comparison",
    x = "Date", y = "LAI", color = "Well ID"
  ) +
  theme_minimal() +
  #theme(panel.grid = element_blank(),
  #      legend.position = "right")
  theme(
    legend.position = "right",
    #panel.background = element_rect(fill="white"),
    panel.grid.major.x = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dotted", linewidth = 0.1),
    panel.grid.major.y = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.y = element_line(color = "gray", linetype = "dotted", linewidth = 0.1))

w_plot_file = paste(repository_dir, LAI_plots_dir,
                           'LAI_willow_timeseries.jpg',
                           sep='')

ggsave(
  filename = w_plot_file,
  plot = w_plot,
  width = 8,
  height = 6,
  units = "in",
  dpi = 300
)

#---------------------------------------------------------
#PART(2): Statistics

#Step(1): Creates a well-level summary table: each row = one willow well
#(i): Numeric columns: averaged over time
#(ii): Logical columns: well-level identifiers

willow_means <- data_corrected %>%
  filter(is_willow) %>%
  group_by(well_id) %>%
  summarise(
    #(i)
    LAI.sensor = mean(LAI.sensor, na.rm = TRUE),
    LAI.rmWAI = mean(LAI.rmWAI, na.rm = TRUE),
    LAI.halfWAI = mean(LAI.halfWAI, na.rm = TRUE),
    #(ii)
    is_east = any(is_east),
    is_kiln = any(is_kiln),
    is_riparian = any(is_riparian),
    is_terrace = any(is_terrace),
    is_fan = any(is_fan),
    .groups = "drop"
  )

#---------------------------------------------------------
#Step(2): t-test for east/kiln (two groups)
t.test(LAI.sensor ~ is_east, data = willow_means)
t.test(LAI.rmWAI ~ is_east, data = willow_means)
t.test(LAI.halfWAI ~ is_east, data = willow_means)
tt_row <- function(formula, data, data_type){
  tt <- t.test(formula, data = data)
  tibble(
    data_type = data_type,
    t = unname(tt$statistic),
    df = unname(tt$parameter),
    p_value = unname(tt$p.value),
    conf_low = tt$conf.int[1],
    conf_high = tt$conf.int[2]
  )
}
t_table <- bind_rows(
  tt_row(LAI.sensor ~ is_east, data = willow_means, data_type = "LAI.sensor"),
  tt_row(LAI.rmWAI ~ is_east, data = willow_means, data_type = "LAI.rmWAI"),
  tt_row(LAI.halfWAI ~ is_east, data = willow_means, data_type = "LAI.halfWAI")
)
print(t_table)

# INTERPRETATION FROM CHATGPT
# Welch two-sample t-tests comparing east and kiln wells showed no significant differences in mean LAI for sensor-derived values or for LAI corrected using full or half WAI (all p > 0.25). Confidence intervals for all metrics overlapped zero, indicating no detectable east–kiln effect at the well scale

#---------------------------------------------------------
#Step(3): ANOVA for positions (three groups)
willow_means <- willow_means %>%
  mutate(position = case_when(
    is_riparian ~ "Riparian",
    is_terrace ~ "Terrace",
    is_fan ~ "Fan"
  ))

anova(lm(LAI.sensor ~ position, data = willow_means))
anova(lm(LAI.rmWAI ~ position, data = willow_means))
anova(lm(LAI.halfWAI ~ position, data = willow_means))

anova_row <- function(formula, data, data_type){
  a <- anova(lm(formula, data = data))
  tibble(
    data_type = data_type,
    F = a$`F value`[1],
    df_num = a$Df[1],
    df_den = a$Df[2],
    p_value = a$`Pr(>F)`[1]
  )
}

a_table <- bind_rows(
  anova_row(LAI.sensor ~ position, data = willow_means, data_type = "LAI.sensor"),
  anova_row(LAI.rmWAI ~ position, data = willow_means, data_type = "LAI.rmWAI"),
  anova_row(LAI.halfWAI ~ position, data = willow_means, data_type = "LAI.halfWAI")
)

print(a_table)

# Interpreting ANOVA Output (from ChatGPT)
# It tests Ho: the mean is equal across riparian, terrace and fan
# and H1: at least one position differs
# F: Ratio of between-group to within-group variance
# df_num: Number of groups − 1 (should be 2)
# df_den: Residual degrees of freedom
# p_value: Evidence against equal means
# If p_value > 0.05: no detectable position effect at the well scale
# If p_value < 0.05: followup with TukeyHSD() to identify which positions differ
# but with very small group size, assumptions are weakly testable and power is low;
# so effect size and confidence intervals matter more than p-values
TukeyHSD(aov(LAI.sensor ~ position, data = willow_means))


#---------------------------------------------------------
#Step(4): summary table for willow mean
willow_summary_table <- willow_means %>%
  select(well_id, LAI.sensor, LAI.rmWAI, LAI.halfWAI, is_east, is_kiln, position)

print(willow_summary_table)

#---------------------------------------------------------
#write all tables and graphs
t_table_file = paste(repository_dir, LAI_results_dir,"willow_ttest_results.csv",sep='')
a_table_file = paste(repository_dir, LAI_results_dir,"willow_anova_results.csv",sep='')
mean_file = paste(repository_dir, LAI_results_dir,"willow_mean_by_well.csv",sep='')

write.csv(t_table,
          t_table_file,
          row.names = FALSE)

write.csv(a_table,
          a_table_file,
          row.names = FALSE)

write.csv(willow_summary_table,
          mean_file,
          row.names = FALSE)
#ggsave(
#  filename = "willow_LAI_timeseries.png",
#  plot = last_plot(),
#  width = 12,
#  height = 9,
#)
#---------------------------------------------------------

#PART(1): Plotting for Sedge LAI

#---------------------------------------------------------
#Step(1): Data preparation
# Change the data frame from wide - long, format for ggplot

df_sedge_long <- data_corrected %>%
  filter(is_sedge) %>%
  #(ii)
  pivot_longer(
    cols = c(LAI.sensor, LAI.rmWAI, LAI.halfWAI),
    names_to = "data_type",
    values_to = "value"
  )

#---------------------------------------------------------
#Step(2): Calculate mean across wells per Date + data type
df_sedge_mean <- df_sedge_long %>%
  group_by(Date, data_type) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop")

#---------------------------------------------------------
#Step(3): plot and save
s_plot <- ggplot(df_sedge_long, aes(x = Date, y = value)) +
  geom_line(aes(group = well_id, color = well_id), alpha = 0.6) +
  geom_line(
    data = df_sedge_mean,
    aes(x = Date, y = mean_value, group = 1),
    color = "black",
    linewidth = 1.2
  ) +
  theme_minimal() +
  theme(
    legend.position = "right",
    #panel.background = element_rect(fill="white"),
    panel.grid.major.x = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dotted", linewidth = 0.1),
    panel.grid.major.y = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.y = element_line(color = "gray", linetype = "dotted", linewidth = 0.1))


s_plot_file = paste(repository_dir, LAI_plots_dir,
                    'LAI_sedge_timeseries.jpg',
                    sep='')

ggsave(
  filename = s_plot_file,
  plot = s_plot,
  width = 8,
  height = 6,
  units = "in",
  dpi = 300
)

#---------------------------------------------------------

#PART(2): Statistics

#Step(1): Creates a well-level summary table: each row = one sedge well
#(i): Numeric columns: averaged over time
#(ii): Logical columns: well-level identifiers

sedge_means <- data_corrected %>%
  filter(is_sedge) %>%
  group_by(well_id) %>%
  summarise(
    #(i)
    LAI.sensor = mean(LAI.sensor, na.rm = TRUE),
    #(ii)
    is_east = any(is_east),
    is_kiln = any(is_kiln),
    is_riparian = any(is_riparian),
    is_terrace = any(is_terrace),
    is_fan = any(is_fan),
    .groups = "drop"
  )
#---------------------------------------------------------
#Step(2): t-test for east/kiln (two groups)
t.test(LAI.sensor ~ is_east, data = sedge_means)
tt_row <- function(formula, data, data_type){
  tt <- t.test(formula, data = data)
  tibble(
    data_type = data_type,
    t = unname(tt$statistic),
    df = unname(tt$parameter),
    p_value = unname(tt$p.value),
    conf_low = tt$conf.int[1],
    conf_high = tt$conf.int[2]
  )
}
t_table <- bind_rows(
  tt_row(LAI.sensor ~ is_east, data = sedge_means, data_type = "LAI.sensor"),
)
print(t_table)
#---------------------------------------------------------
#Step(3): ANOVA for positions (three groups)
sedge_means <- sedge_means %>%
  mutate(position = case_when(
    is_riparian ~ "Riparian",
    is_terrace ~ "Terrace",
    is_fan ~ "Fan"
  ))
anova(lm(LAI.sensor ~ position, data = sedge_means))
anova_row <- function(formula, data, data_type){
  a <- anova(lm(formula, data = data))
  tibble(
    data_type = data_type,
    F = a$`F value`[1],
    df_num = a$Df[1],
    df_den = a$Df[2],
    p_value = a$`Pr(>F)`[1]
  )
}

a_table <- bind_rows(
  anova_row(LAI.sensor ~ position, data = sedge_means, data_type = "LAI.sensor"),
)

print(a_table)
#---------------------------------------------------------
#Step(4): summary table for sedge mean
sedge_summary_table <- sedge_means %>%
  select(well_id, LAI.sensor, is_east, is_kiln, position)

print(sedge_summary_table)

#---------------------------------------------------------
#write all tables and graphs
t_table_file = paste(repository_dir, LAI_results_dir,"sedge_ttest_results.csv",sep='')
a_table_file = paste(repository_dir, LAI_results_dir,"sedge_anova_results.csv",sep='')
mean_file = paste(repository_dir, LAI_results_dir,"sedge_mean_by_well.csv",sep='')

write.csv(t_table,
          t_table_file,
          row.names = FALSE)

write.csv(a_table,
          a_table_file,
          row.names = FALSE)

write.csv(sedge_summary_table,
          mean_file,
          row.names = FALSE)

#---------------------------------------------------------

#PART(1): Plotting for Mixed Herbaceous LAI

#---------------------------------------------------------
#Step(1): Data preparation
# Change the data frame from wide - long, format for ggplot

df_herb_long <- data_corrected %>%
  filter(is_herbaceous) %>%
  #(ii)
  pivot_longer(
    cols = c(LAI.sensor),
    names_to = "data_type",
    values_to = "value"
  )

#---------------------------------------------------------
#Step(2): Calculate mean across wells per Date + data type
df_herb_mean <- df_herb_long %>%
  group_by(Date, data_type) %>%
  summarise(mean_value = mean(value, na.rm = TRUE), .groups = "drop")

#---------------------------------------------------------
#Step(3): plot and save
h_plot <- ggplot(df_herb_long, aes(x = Date, y = value)) +
  geom_line(aes(group = well_id, color = well_id), alpha = 0.6) +
  geom_line(
    data = df_herb_mean,
    aes(x = Date, y = mean_value, group = 1),
    color = "black",
    linewidth = 1.2
  ) +
  theme_minimal() +
  theme(
    legend.position = "right",
    #panel.background = element_rect(fill="white"),
    panel.grid.major.x = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.x = element_line(color = "gray", linetype = "dotted", linewidth = 0.1),
    panel.grid.major.y = element_line(color = "gray", linetype = "solid", linewidth = 0.1),
    panel.grid.minor.y = element_line(color = "gray", linetype = "dotted", linewidth = 0.1))


h_plot_file = paste(repository_dir, LAI_plots_dir,
                    'LAI_mixedHerb_timeseries.jpg',
                    sep='')

ggsave(
  filename = h_plot_file,
  plot = h_plot,
  width = 8,
  height = 6,
  units = "in",
  dpi = 300
)

#---------------------------------------------------------

#PART(2): Statistics

#Step(1): Creates a well-level summary table: each row = one sedge well
#(i): Numeric columns: averaged over time
#(ii): Logical columns: well-level identifiers

herb_means <- data_corrected %>%
  filter(is_herbaceous) %>%
  group_by(well_id) %>%
  summarise(
    #(i)
    LAI.sensor = mean(LAI.sensor, na.rm = TRUE),
    #(ii)
    is_east = any(is_east),
    is_kiln = any(is_kiln),
    is_riparian = any(is_riparian),
    is_terrace = any(is_terrace),
    is_fan = any(is_fan),
    .groups = "drop"
  )
#---------------------------------------------------------
#Step(2): t-test for east/kiln (two groups)
t.test(LAI.sensor ~ is_east, data = herb_means)
tt_row <- function(formula, data, data_type){
  tt <- t.test(formula, data = data)
  tibble(
    data_type = data_type,
    t = unname(tt$statistic),
    df = unname(tt$parameter),
    p_value = unname(tt$p.value),
    conf_low = tt$conf.int[1],
    conf_high = tt$conf.int[2]
  )
}
t_table <- bind_rows(
  tt_row(LAI.sensor ~ is_east, data = herb_means, data_type = "LAI.sensor"),
)
print(t_table)
#---------------------------------------------------------
#Step(3): ANOVA for positions (three groups)
herb_means <- herb_means %>%
  mutate(position = case_when(
    is_riparian ~ "Riparian",
    is_terrace ~ "Terrace",
    is_fan ~ "Fan"
  ))
anova(lm(LAI.sensor ~ position, data = herb_means))
anova_row <- function(formula, data, data_type){
  a <- anova(lm(formula, data = data))
  tibble(
    data_type = data_type,
    F = a$`F value`[1],
    df_num = a$Df[1],
    df_den = a$Df[2],
    p_value = a$`Pr(>F)`[1]
  )
}

a_table <- bind_rows(
  anova_row(LAI.sensor ~ position, data = herb_means, data_type = "LAI.sensor"),
)

print(a_table)
#---------------------------------------------------------
#Step(4): summary table for sedge mean
herb_summary_table <- herb_means %>%
  select(well_id, LAI.sensor, is_east, is_kiln, position)

print(herb_summary_table)

#---------------------------------------------------------
#write all tables and graphs
t_table_file = paste(repository_dir, LAI_results_dir,"herb_ttest_results.csv",sep='')
a_table_file = paste(repository_dir, LAI_results_dir,"herb_anova_results.csv",sep='')
mean_file = paste(repository_dir, LAI_results_dir,"herb_mean_by_well.csv",sep='')

write.csv(t_table,
          t_table_file,
          row.names = FALSE)

write.csv(a_table,
          a_table_file,
          row.names = FALSE)

write.csv(herb_summary_table,
          mean_file,
          row.names = FALSE)
