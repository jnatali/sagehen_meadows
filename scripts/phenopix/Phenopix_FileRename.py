from PIL import Image
import os
import shutil

#this numeric value maps to the timestamp metadata
DATE_TIME_TAG = 36867

# path to the root image directory, will be processed recursively
ROOT = "/Users/jnat/Box/gradSchool/Projects/SierraMeadows_Research/2018_ISEECI_Meadows/Data/Sagehen/Data/phenocam/phenocam_2018"
DESTINATION = "RENAMED"
#destination directory
IMG_DEST = os.path.join(ROOT, DESTINATION)


def renameImage(fullPath, destPath):
        #ensure destination directory exists
        createDestDir(destPath)
        image = Image.open(fullPath)

        # extract datetime from the meta tags
        exifdata = image.getexif()
        dateTimeStamp = exifdata.get(DATE_TIME_TAG)

        dateParts = dateTimeStamp.split(" ")
        year = dateParts[0].replace(":", "_")
        time = dateParts[1].split(":")

        #filename is yyyy_mm_dd_HHMM.jpg
        fullPathUpdated = os.path.join(destPath , year + "_" + time[0] + time[1] + ".jpg")
        print("Copying to " ,fullPathUpdated)
        shutil.copy(fullPath, fullPathUpdated)


def processDirectory(path):
    listOfFiles = os.listdir(path)
    for filename in listOfFiles:
        if not(os.path.isdir(os.path.join(path,filename))):

            #process files in current directory
            if(filename.upper().endswith(".JPG")):

                destPath = os.path.join(path,DESTINATION)
                fullPath = os.path.join(path, filename)
                print("Processing " , fullPath)
                renameImage(fullPath, destPath)

            else:
                print ("************* Skipping " , filename + " *************")

        #then recurse over subdirectorires
        else:

            if  not(DESTINATION in filename):
                print("Processing subdirectory ", filename)
                processDirectory(os.path.join(path, filename))
            else:
                print ("************* Skipping " , filename + " *************")

def createDestDir(destPath):
    #create the destination folder if needed
    if not os.path.exists(destPath):
        os.makedirs(destPath)




#start the walk through the folders starting from ROOT
processDirectory(ROOT)
print("*************** FINISHED IMAGE PROCESSING ***************")




