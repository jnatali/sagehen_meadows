library(phenopix)
setwd("/Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/phenocam/phenopix/RGB")

#Create folders for different outputs
my.path <- structureFolder(path=getwd(),showWarnings=TRUE)

path_img_ref=paste(getwd(),"/REF/",sep='')
roi.path=paste(getwd(),"/ROI",sep='')
img.path=paste(getwd(),"/IMG",sep='')
vi.path=paste(getwd(),"/VI",sep='')

#Create ROI(s) for each meadow
#windows() #- not using, mine pops up under 'Plots' window
DrawMULTIROI(path_img_ref = path_img_ref,path_ROIs = roi.path, 
             nroi=3,file.type=".JPG")
load(paste(roi.path,'/roi.data.Rdata',sep=''))

