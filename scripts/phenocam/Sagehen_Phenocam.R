library(phenopix)
setwd("F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/RGB")

#Create folders for different outputs
my.path <- structureFolder(path=getwd(),showWarnings=TRUE)

path_img_ref="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/RGB/REF/"
roi.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/RGB/ROI/"
img.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/RGB/IMG/"
vi.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/RGB/VI/"

#Create a ROI for Pepperweed
windows()
DrawMULTIROI(path_img_ref = path_img_ref,path_ROIs = roi.path, 
             nroi=1,file.type=".jpg")
load('ROI/roi.data.Rdata')

#extract Vegetation Indices
extractVIs(img.path=img.path,roi.path=roi.path,vi.path=vi.path,plot=TRUE,begin="2018-01-01",
           date.code="yyyy_mm_dd_HHMM",file.type=".jpg",npixels=3)

load('VI/2018-01-01_2019-08-01_VI.data.Rdata')
names(VI.data[[1]])

#Autofilter
df=as.data.frame(VI.data$roi1) #creates a dataframe from vegetation indices
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


# Second focus on 2018 data, with multiple ROIs ---------------------------
library(phenopix)
setwd("F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/2018")

#Create folders for different outputs
my.path <- structureFolder(path=getwd(),showWarnings=TRUE)

path_img_ref="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/2018/REF/"
roi.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/2018/ROI/"
img.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/2018/IMG/"
vi.path="F:/PostDoc/Data/Preliminary Analysis/RushRanch/Phenocam/2018/VI/"

#Create ROIs
windows()
DrawMULTIROI(path_img_ref = path_img_ref,path_ROIs = roi.path, 
             nroi=1,roi.names=c("Grass"),file.type=".jpg")
load('ROI/roi.data.Rdata')

extractVIs(img.path=img.path,roi.path=roi.path,vi.path=vi.path,plot=TRUE,
           date.code="yyyy_mm_dd_HHMM",file.type=".jpg",npixels=3)

load('VI/VI.data.Rdata')
write.csv(VI.data$Tule,"PhenoData_Tule.csv")
