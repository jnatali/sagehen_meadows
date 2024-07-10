library(phenopix)
library(raster)

# Wrapper function to draw multiple ROIs
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
    img_rois <- list()
    for (i in seq_len(nroi)) {
      quartz()
      plotRGB(img)
      mtext(paste("ROI ", i, " - ", roi.names[i], " \n a) n left mouse button clicks on ROI vertices (n>=3) \n b) 1 right mouse button click to close the polygon", 
                  sep = ""), side = 3, line = -5)
      pol.all <- NULL
      repeat {
        pol1 <- drawPoly(sp = TRUE, col = "red", lwd = 2)
        message("Are you done with your ROI? (y/n): ")
        answer <- readline()
        if (tolower(answer) == "y") {
          pol.all <- c(pol.all, pol1)
          break
        } else {
          pol.all <- c(pol.all, pol1)
        }
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
      coordinates <- data.frame(rowpos = coordinates(vertices)[, 1], colpos = coordinates(vertices)[, 2])
      
      dev.print(jpeg, file = paste(path_ROIs, "/ROI", i, "_", roi.names[i], ".jpg", sep = ""), width = 1024, height = 1024)
      dev.off()
      
      out <- list(mask = masked.img, polygons = vertices)
      img_rois[[i]] <- out
    }
    roi.data[[basename(file)]] <- img_rois
  }
  
  save(roi.data, file = paste(path_ROIs, "/roi.data.Rdata", sep = ""))
  return(invisible(roi.data))
}

setwd("/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB")

# Create folders for different outputs
my.path <- structureFolder(path = getwd(), showWarnings = TRUE)

path_img_ref <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/REF/RENAMED"
roi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/ROI"
img.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/IMG/RENAMED"
vi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/VI"

# Create ROI(s) for each meadow
DrawMULTIROI_Wrapper(path_img_ref = path_img_ref, path_ROIs = roi.path, nroi = 3, file.type = ".jpg")
