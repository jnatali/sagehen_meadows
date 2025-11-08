FROM rocker/geospatial:latest

# Install phenopix dependencies
RUN R -e "install.packages('remotes', repos='https://cloud.r-project.org')" \
    && R -e "remotes::install_github('cran/phenopix')"

# Create working directory
WORKDIR /app

# Copy any local R scripts (optional)
# COPY ./scripts /app/scripts

# Default command
CMD ["R"]
