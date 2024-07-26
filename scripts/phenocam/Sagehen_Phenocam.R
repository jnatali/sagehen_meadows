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

path_img_ref <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/REF"
roi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/ROI"
img.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/IMG"
vi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/VI"

# Create ROI(s) for each meadow
DrawMULTIROI_Wrapper(path_img_ref = path_img_ref, path_ROIs = roi.path, nroi = 3, file.type = ".jpg")

load('ROI/roi.data.Rdata')


#EDIT BELOW

extractVIs(img.path=img.path,roi.path=roi.path,vi.path=vi.path,plot=TRUE,begin="sagee1_2018_05_16_1323",
           date.code="yyyy_mm_dd_HHMM",file.type=".jpg",npixels=3)

load("/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/VI/VI.data.Rdata")

# Extract the date from the formatted filename
filename <- 'sagee1_2018_05_16_1323.jpg'
extractDateFilename(filename, date.code='yyyy_mm_dd_HHMM')

class(VI.data[[1]])
head(names(VI.data[[1]]))

# Check the structure of VI.data
str(VI.data[[1]][[1]])

# Define the path where you want to save the CSV
csv_file_path <- "VI_data.csv"

# Write the data frame to a CSV file
write.csv(VI.data, file = csv_file_path, row.names = FALSE)


## when running this, it seems there is nothing in spatial.list, meaning I don't think VI is being extracted correctly. I should also see red, green, blue data columns
spatialFilter(spatial.list, filter = c("night", "spline", "max"),
          filter.options = NULL, ncores = "all", log.file = NULL)












#Autofilter
df <- as.data.frame(VI.data$`2018_05_16_1323`) #creates a dataframe from vegetation indices
str(df)
colnames(df)

# Apply the autoFilter function

filtered.data <- autoFilter(df,filter=c('night','max'),plot=TRUE,na.fill=TRUE) #removes noise in vegetation indices
#Night filter removes value below gcc of 0.2
#Max filter computes the 90% of the curve based on a 3-day moving window (following Sonnetag et al. 2012)


#Fit spline
greenProcess(filtered.data$max.filtered,'spline','trs',plot=TRUE)

#Convert inputs into dataframe
library(zoo)
df=fortify.zoo(filtered.data)
df$Index=as.Date(df$Index,format="%yyyy/%mm/%dd")
plot.ts(df$Index,df$max.filtered)

#Plot data
library(reshape)
df=read.csv("FilteredData.csv",sep=",")
df.2017=subset(df,df$Year==2017)

windows()
par(mfrow=c(4,1),mar=c(3,4,1,1))
plot(df.2017$DOY,df.2017$bcc,pch=16,col="royalblue3",xlab="DOY",ylab="BCC")
plot(df.2017$DOY,df.2017$max.filtered,pch=16,col="springgreen3",xlab="DOY",ylab="GCC")
plot(df.2017$DOY,df.2017$rcc,pch=16,col="red3",xlab="DOY",ylab="RCC")
plot(df.2017$DOY,df.2017$grR,pch=16,col="black",xlab="DOY",ylab="Green-Red Ratio")

#2018
df.2018=subset(df,df$Year==2018)

windows()
par(mfrow=c(4,1),mar=c(3,4,1,1))
plot(df.2018$DOY,df.2018$bcc,pch=16,col="royalblue3",xlab="DOY",ylab="BCC")
plot(df.2018$DOY,df.2018$max.filtered,pch=16,col="springgreen3",xlab="DOY",ylab="GCC")
plot(df.2018$DOY,df.2018$rcc,pch=16,col="red3",xlab="DOY",ylab="RCC")
plot(df.2018$DOY,df.2018$grR,pch=16,col="black",xlab="DOY",ylab="Green-Red Ratio")


