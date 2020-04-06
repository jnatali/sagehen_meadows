from PIL import Image
import os
import shutil

#this numeric value maps to the timestamp metadata
DATETIMEORIGINALTAG = 36867

# path to the image directory
imageDir = "./images"
#destination directory
imageDest = imageDir + "/renamed"

#create the destination folder if needed
if not os.path.exists(imageDest):
    os.makedirs(imageDest)

for filename in os.listdir(imageDir):

    #only process jpgs
    if(filename.upper().endswith(".JPG")):
        fullPath = imageDir + "/" + filename
        print("processing " , fullPath)
        image = Image.open(fullPath)


        # extract datetime from the meta tags
        exifdata = image.getexif()
        dateTimeStamp = exifdata.get(DATETIMEORIGINALTAG)

        dateParts = dateTimeStamp.split(" ")
        year = dateParts[0].replace(":", "_")
        time = dateParts[1].split(":")

        #filename is yyyy_mm_dd_HHMM.jpg
        fullPathUpdated = imageDest + "/" + year + "_" + time[0] + time[1] + ".jpg"
        print("moving " ,fullPathUpdated)
        shutil.copy(fullPath, fullPathUpdated)

    else:
        print ("************* skipping " , filename + " *************")

