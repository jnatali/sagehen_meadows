library(phenopix)
library(raster)
library(gtools)

# Wrapper function -- DrawMULTIROI kept giving me error in brick function
DrawMULTIROI_Wrapper <- function(path_img_ref, path_ROIs, nroi = 1, roi.names = NULL, file.type = ".jpg") {
  if (is.null(roi.names)) 
    roi.names <- paste0("roi", 1:nroi)
  files <- list.files(path = path_img_ref, pattern = file.type, full.names = TRUE)
  if (length(files) == 0) {
    stop("No files found in the specified directory with the given file type.")
  }
  
  roi.data <- list()
  for (file in files) {
    img <- brick(file)
    for (i in seq(as.numeric(nroi))) {
      quartz()
      plotRGB(img)
      mtext(paste("ROI ", i, " - ", roi.names[i], " \n a) n left mouse button clicks on ROI vertexes (n>=3) \n b) 1 right mouse button click to close the polygon", 
                  sep = ""), side = 3, line = -5)
      answer <- "n"
      pol.all <- NULL
      while (answer == "n") {
        pol1 <- drawPoly(sp = TRUE, col = "red", lwd = 2)
        answer <- ask("are you done with roi? \n type y or n")
        pol.all <- c(pol.all, pol1)
      }
      if (length(pol.all) == 1) 
        vertices <- pol.all[[1]]
      else {
        vertices <- do.call(bind, pol.all)
      }
      white.mask <- img[[1]]
      raster::values(white.mask) <- 1
      masked.img <- mask(white.mask, vertices)
      raster::values(masked.img)[is.na(values(masked.img))] <- 0
      coordinates <- data.frame(rowpos = coordinates(vertices)[, 
                                                               1], colpos = coordinates(vertices)[, 2])
      dev.print(jpeg, file = paste(path_ROIs, "/ROI", i, "_", 
                                   roi.names[i], ".jpg", sep = ""), width = 1024, height = 1024)
      dev.off()
      out <- c(masked.img, vertices)
      names(out) <- c("mask", "polygons")
      roi.data[[i]] <- out
    }
  }
  names(roi.data) <- roi.names
  save(roi.data, file = paste(path_ROIs, "roi.data.Rdata", 
                              sep = ""))
  return(invisible(roi.data))
}

# TODO: Can we add a string to set the user's base directory one time,
#       e.g. basedir = "/Users/play". Then assume the directory structure
#       will be phenocam/phenopix based on the github code, so add another
#       string variable, phenodir.
#       And we can use basdir + phenodir to setwd, and path_img_ref, etc.
#       And let's set that string at the top of the file, so it's
#       easy to access/change without scrolling through the code.

# Use the wrapper function
setwd("/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/scripts/phenocam")

# Create folders for different outputs
my.path <- structureFolder(path=getwd(), showWarnings=TRUE)

path_img_ref <- "/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/scripts/phenocam/REF"
roi.path <- "/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/scripts/phenocam/ROI"
img.path <- "/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/scripts/phenocam/IMG"
vi.path <- "/Volumes/SANDISK_SSD_G40/GoogleDrive/GitHub/sagehen_meadows/scripts/phenocam/VI"

# Create ROI(s) for each meadow
#quartz()
#quartz.options(reset = FALSE)
roi_names = as.character("willow","sedge","mixed herb")
DrawMULTIROI_Wrapper(path_img_ref = path_img_ref, path_ROIs = roi.path, 
                     nroi = 3, roi.names = roi_names, file.type = ".jpg")

# Load the ROI data
roi_data_path <- file.path(roi.path, "roi.data.Rdata")
load(roi_data_path)

