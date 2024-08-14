library(phenopix)
library(raster)

setwd("/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB")

#Create folders for different outputs
my.path <- structureFolder(path=getwd(),showWarnings=TRUE)

path_img_ref <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/REF/"
roi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/ROI/"
img.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/IMG/SE1RENAMED/"
vi.path <- "/Users/play/Documents/GitHub/sagehen_meadows/data/phenocam/phenopix/RGB/VI/"


quartz()
DrawMULTIROI(path_img_ref = path_img_ref,path_ROIs = roi.path, 
             nroi=3,file.type=".jpg")
load('ROI/roi.data.Rdata')

PrintROI(path_img_ref = 'REF/sagee1_2018_05_16_1323.jpg', path_ROIs = 'ROI/', which = 'all', file.type='.jpg')

##removed begin=
extractVIs(img.path=img.path,roi.path=roi.path,vi.path=vi.path,plot=TRUE, spatial = FALSE, 
           date.code="yyyy_mm_dd_HHMM",file.type=".jpg",npixels=3, bind = FALSE)

load('VI/VI.data.Rdata')
summary(VI.data)
names(VI.data.[[1]])

df=as.data.frame(VI.data$roi1) #creates a dataframe from vegetation indices
filtered.data <- autoFilter(df,filter=c('night','max'),plot=TRUE,na.fill=TRUE) #removes noise in vegetation indices
