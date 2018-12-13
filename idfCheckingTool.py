"""
    IDF Checking Tool v0.2 by Braden Kallin
    Additional credit to Alvin Su
    
    Purpose: To check IDF 3.0 (.emn) data for errors. IDF data is generated from
               CircuitWorks to be imported into CADSTAR using standard processes.

    Notes: The "emnObj" and "shape" classes do most of the heavy lifting in
             this program. 
           This program is intended to be expanded as long as we're using
             circuitworks to generate IDF 3.0 data for MCAD/ECAD data transfer
"""

import sys
import traceback
import os
import glob
import emnObj

startDir = os.getcwd()

"""
    Read some .emn files, read in the parts libraries (if available),
      then run checks on the .emn files and print the errors.
"""
def main():
    emnsToCheck = []

    partsLibrary = importLibrary() #store a list of library parts in memory
    #libReadTest(partsLibrary) #write the library list contents to a file

    print("IDF CHECKING TOOL v0.2\n")

    userIn = input("Drop one .emn file here and press return,\n" +
        "or press return to check all .emn files in the current directory.\n" +
        ">> ")

    userIn = userIn.replace('\"','') #strip quotes

    if userIn == '': #user just pressed return
        emnsToCheck = getEmnsInFolder()
    else:
        emnsToCheck = getDraggedFile(userIn)

    #check for errors and show them to the user
    if emnsToCheck: 
        for currentEmn in emnsToCheck:
            print("\nChecking %s..." % currentEmn.__str__())
            currentEmn.checkAllErrors(partsLibrary)
            currentEmn.printAllErrors()

        #prompt the user to save errors to a log
        userIn = input("Save these results to idferrors.log? (y/n): ")
        print("")
        if userIn.lower().strip() == 'y':
            with open("idferrors.log","w") as f:
                for currentEmn in emnsToCheck:
                    f.write("%s:\n" % currentEmn.__str__())
                    for currentError in currentEmn.errors:
                        f.write("%s\n" % currentError)
                    f.write("\n")

    else:
        print("Did not find any .emn data to check.\n")

#==============================================================================

"""
    Search the current working directory for .emn files,
      then build emnObjs and put those objects into a list.
"""
def getEmnsInFolder():
    emnObjList = []

    for file in glob.glob("*.emn"):
        lineList = []
        with open(file) as f:
            for line in f: #read each line of the file
                lineList.append(line)
        newEmnObj = emnObj.emnObj(lineList,file) #build an emnObj
        emnObjList.append(newEmnObj) #put emnObjs in a list

    if emnObjList:
        print("Checking all .emn files in current working directory.")

    return emnObjList

"""
    Get the filename from the main function, build an emnObj from 
     the lines in the file, then put the emnObj into a list.
"""
def getDraggedFile(userIn):
    emnObjList = []
    lineList = []
    fileName = userIn.split('\\')[-1] #get the filename without the path

    if '.emn' in fileName[-4:]: 
        with open(userIn) as f:
            for line in f:      
                lineList.append(line)
        newEmnObj = emnObj.emnObj(lineList,fileName) 
        emnObjList.append(newEmnObj)

    return emnObjList

"""
    Check if CADSTAR part libraries are available,
      then read all the part numbers from the library into a list.
"""
def importLibrary(): 
    foundLib = True
    libPath = ""
    partsLib = [] #start a list of parts

    #check to see if the library paths are accessible
    #  first check locally, then check the network
    try: 
        libPath = r"C:\csdat\library"
        print("Checking local drive for parts library...")
        os.chdir(libPath)
    except:
        try:
            libPath = r"\\bombay.ad.garmin.com\data\CSWIN\LIBRARY"
            print("Checking network for parts library...")
            os.chdir(libPath)
        except:
            foundLib = False
            print(" could not find parts library.\n")

    if foundLib:
        print(" found parts library!\n")

        validTopLibs = [ #valid libraries in the top level
        '800899.LIB','900904.LIB','600799.LIB','000199.LIB',
        '400599.LIB','905XXX.LIB','906999.LIB','200399.LIB',
        'NOGARPN.LIB','TEMP.LIB'
        ]

        #read in top-level library parts
        for libFile in glob.glob("*.LIB"):
            if libFile in validTopLibs:
                partsLib.extend(readLibFile(libFile))
                
        #read LIB files in LIB folders
        for root, dirs, files in os.walk("."):
            for dirName in dirs:
                if (dirName != "LIBRARIAN" and
                    dirName.startswith("LIB") or 
                    dirName.startswith("lib")):
                    newPath = libPath + "\\" + dirName
                    os.chdir(newPath)
                    for libFile in glob.glob("*.LIB"):
                        if libFile.startswith("LIB"):
                            partsLib.extend(readLibFile(libFile))

    #go back to the folder we started in.
    os.chdir(startDir)
    
    return partsLib

"""
    Read a .lib file and do some conditioning to get a list of part numbers.
"""
def readLibFile(libFile):
    currentLibParts = []

    #all/only part numbers start with single quotes
    for currentLine in open(libFile):
        if currentLine.startswith("\'"):
            currentLibParts.append(currentLine)

    #remove ampersands, single quotes, whitespace, case
    for i in range(len(currentLibParts)):
        currentLibParts[i] = currentLibParts[i].replace("&", "")
        currentLibParts[i] = currentLibParts[i].replace("\'", "")
        currentLibParts[i] = currentLibParts[i].strip()
        currentLibParts[i] = currentLibParts[i].upper()

    return currentLibParts

"""
    Write all the parts in the partsLibrary list to a file
"""
def libReadTest(partsLibrary):
    with open("libFile","w") as f:
        for item in partsLibrary:
            f.write("%s\n" % item)

"""
    Run the main function
"""
if __name__ == '__main__':
    try:
        main()
    except OSError as e:
        if(e.filename):
            print("Could not access %s" % e.filename)
    except:
        print("An error occurred. Here's what the program has to say about it:")
        traceback.print_tb(sys.exc_info()[2])
        print("")
    finally:
        os.system('pause')