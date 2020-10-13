library(phenex)
library(phenopix)
library(hydroTSM)
library(greenbrown)
library(psych)

setwd('E:/Dissertation/Chap3_Phenology/Data/Phenocam/WestPond') #Folder in which your files should be saved
path=getwd()
structureFolder(path) #Automatically generates a series of folders

roi.path="E:/Dissertation/Chap3_Phenology/Data/Phenocam/WestPond/2015/ROI/" #Let's R know where to find the different folders. Change as needed.
vi.path = "E:/Dissertation/Chap3_Phenology/Data/Phenocam/WestPond/2015/VI/"
images="E:/Dissertation/Chap3_Phenology/Data/Phenocam/WestPond/2015/IMG/"
ref="E:/Dissertation/Chap3_Phenology/Data/Phenocam/WestPond/2015/REF/"

windows() #Opens a new window.You will need that to draw the ROI.
DrawROI(path_img_ref=ref,path_ROIs=roi.path,nroi=1,file.type='.jpg') # Draws the ROI. See step #4 in tutorial

extractVIs(img.path=images,roi.path=roi.path,vi.path=vi.path,plot=TRUE,date.code="yyyy_mm_dd_HHMMSS",npixels=5,file.type='.jpg') #extract vegetation indices within every image.
load('VI/VI.data.Rdata') #Loads the vegetation data

#Autofilter
df=as.data.frame(VI.data$roi1) #creates a dataframe from vegetation indices
filtered.data <- autoFilter(df[1:3890,],filter=c('night','max'),plot=TRUE) #removes noise in vegetation indices

df.filtered=(data.frame(index(filtered.data$max.filtered), as.data.frame(filtered.data$max.filtered)))#Convert to dataframe
colnames(df.filtered)=c('Date','GCC')
df.filtered$DOY <- strftime(df.filtered$Date, format = "%j")
#generate spline
sp1=spline(x=df.filtered$DOY,y=df.filtered$GCC,method="natural",xmin=min(1),xmax=max(365),xout=1:365)
sp2=smooth.spline(x=sp1$x, y=sp1$y,df=7)
plot(sp2$x,sp2$y)

#generate stats
pos.evi=subset(sp2$y,sp2$y>0)
indvi=sum(pos.evi)
stats=describe(x=sp2$y)
relative=(stats$range/indvi)
quantile = quantile(sp2$y,c(0.10, 0.25,0.30, 0.50, 0.75,0.80,0.90))
quantile.t=t(as.data.frame(quantile))
date.seq=(seq(as.Date('2016/01/01'),as.Date('2016/12/31'),by='day'))
spline.ts=zoo(sp2$y,order.by=date.seq)

spline <- greenProcess(spline.ts,fit='spline',threshold='derivatives',plot=TRUE,nrep=999,envelope="min-max",hydro=FALSE,uncert=TRUE)
metrics = as.data.frame(spline$metrics)
site="WP"
year=2016
pheno.metrics=cbind(site,year,metrics[2,],indvi,relative,stats,quantile.t)

df.dat=cbind(sp2$x,sp2$y)
write.csv(pheno.metrics,"WP_2016_PhenologyMetrics_Phenocam.csv")
write.csv(df.dat,"WP_2016_GrowingCurve.csv")

#Export smoothed phenological curve (see tutorial step #7)
spl=as.data.frame(extract(spline,what='metrics'))
elmore=as.data.frame(extract(elmore,what='fitted'))
write.csv(spline,"MayberryFarms_2012_Spline.csv")#Change name of site and year as needed.
write.csv(elmore,"MayberryFarms_2012_Elmore.csv")#Change name of site and year as needed.