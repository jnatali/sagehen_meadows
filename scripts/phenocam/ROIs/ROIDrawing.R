library(phenopix)
setwd("/Volumes/MeadowRAP/phenocam/Phenopix/RGB")

#Create folders for different outputs
my.path <- structureFolder(path=getwd(),showWarnings=TRUE)

path_img_ref="/Volumes/MeadowRAP/phenocam/Phenopix/RGB/REF/"
roi.path="/Volumes/MeadowRAP/phenocam/Phenopix/RGB/ROI/"
img.path="/Volumes/MeadowRAP/phenocam/Phenopix/RGB/IMG/"
vi.path="/Volumes/MeadowRAP/phenocam/Phenopix/RGB/VI/"


#Create ROI(s) for each meadow
# windows() - not using, mine pops up under 'Plots' window
DrawMULTIROI(path_img_ref = path_img_ref,path_ROIs = roi.path, 
             nroi=1,file.type=".jpg")
load('/Volumes/MeadowRAP/phenocam/Phenopix/RGB/ROI/roi.data.Rdata')