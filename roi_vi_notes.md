# ROI

Region of Interest per site/camera. 

There should be 3 ROIs per site/camera, 1 for each vegetation type:

willow
sedge
herbaceous

## DrawMULTIROI

To create the ROI polygons representing the vegetation types, run:

```
# TODO: template this for each site/camera
plant_names <- c("willow", "sedge", "herbaceous")
path_to_image <- "data/phenocam/images/2018/sageeast1/2018_05_17_0900.jpg"
path_to_roi <- "data/phenocam/phenopix/2018/sageeast1/ROI/"
DrawMULTIROI(path_to_image, path_to_roi_dir, 3, plant_names)
```

The results will be stored in an `.Rdata` file in the parent of `path_to_roi_dir` (e.g. `data/phenocam/phenopix/2018/sageeast1/ROI/roi.data.Rdata`). This is an R list object of the 3 regions where each region is represented by a raster mask and the polygon as a set of vectors.

There will also be images of each roi polygon overlaid with the underlying jpg in the `path_to_roi_dir` (i.e. `data/phenocam/phenopix/2018/sageeast1/ROI/ROI{1_willow,2_sedge,3_herbaceous}.jpg"`).

Running this from a docker container requires that the host running docker expose the X11 rendering server via socket and permissions. The `docker-compose.yml` is setup to expose this, though you must run `xhost +local:docker` to allow local connections to the x server.

## extractVIs

To create the timeseries of greenness values for each vegetation type, call the `extractVIs` function as follows:

```
# TODO: template this for each site/camera
path_to_image_dir <- "data/phenocam/images/2018/sageeast1"
path_to_roi <- "data/phenocam/phenopix/2018/sageeast1/ROI"
path_to_vi <- "data/phenocam/phenopix/2018/sageeast1/VI/"
log_file <- "data/phenocam/phenopix/2018/sageeast1"
date_code = "yyyy_mm_dd_HHMM"
extractVIs(path_to_image_dir, path_to_roi, path_to_vi, date.code=date_code, log.file=log_file)
```

If running a custom `extractVIs()` defined in `src/extractVIs.R` do the following before running the above:

```
# may need these loaded explicitly if running custom extractVIs function from local source
library(phenopix)
library(raster)
library(parallel)
library(doParallel)
source("src/extractVIs.R")
```
