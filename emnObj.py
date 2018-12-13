"""
    emnObj class: 
        ~store the parts, shapes, units and errors in an emn file
        ~parts and shapes are objects, units and errors are strings.
        ~the error checking suite lives here

    shape class: 
        ~store a shape's outline, cutouts, height and type for use by emnObj

    part class:
        ~store a part's position, name and refdes for use by emnObj
"""

import math

#some definitions from the IDF 3.0 standard
BOARD_START         = ".BOARD_OUTLINE"
BOARD_END           = ".END_BOARD_OUTLINE"
DRILL_START         = ".DRILLED_HOLES"
DRILL_END           = ".END_DRILLED_HOLES"
HEADER_START        = ".HEADER"
HEADER_END          = ".END_HEADER"
OTHER_START         = ".OTHER_OUTLINE"
OTHER_END           = ".END_OTHER_OUTLINE"
PLACE_KEEPOUT_START = ".PLACE_KEEPOUT"
PLACE_KEEPOUT_END   = ".END_PLACE_KEEPOUT"
PLACE_OUTLINE_START = ".PLACE_OUTLINE"
PLACE_OUTLINE_END   = ".END_PLACE_OUTLINE"
PLACEMENT_START     = ".PLACEMENT"
PLACEMENT_END       = ".END_PLACEMENT"
ROUTE_START         = ".ROUTE_OUTLINE"
ROUTE_END           = ".END_ROUTE_OUTLINE"
ROUTE_KEEPOUT_START = ".ROUTE_KEEOUT"
ROUTE_KEEPOUT_END   = ".END_ROUTE_KEEPOUT"
VIA_KEEPOUT_START   = ".VIA_KEEPOUT"
VIA_KEEPOUT_END     = ".END_VIA_KEEPOUT"

SHAPE_STARTS = (
    BOARD_START, OTHER_START, PLACE_KEEPOUT_START, PLACE_OUTLINE_START,
    ROUTE_START, ROUTE_KEEPOUT_START, VIA_KEEPOUT_START
)
SHAPE_ENDS = (
    BOARD_END, OTHER_END, PLACE_KEEPOUT_END, PLACE_OUTLINE_END,
    ROUTE_END, ROUTE_KEEPOUT_END, VIA_KEEPOUT_END
)    

"""
    An emnObj is used to store and manipulate data contained in a .emn file.
    
    When called on to do so (checkAllErrors), an emnObj will do some
      introspection and check itself against IDF/CADSTAR standards,
      then store the errors internally. The emnObj can then be told to
      spill all its flaws to the user (printAllErrors).

    Checks include:
      -checking that all shapes and cutouts are closed
      -checking that cutouts aren't circular
      -checking that height restriction areas aren't 0 height
      -checking that reference designators don't start with "R"
        (mechanical engineers should not be placing resistors)
      -checking that all parts to be placed exist in the library
      -checking that all coordinates are in positive space
      -checking that arcs don't come together at an infinitesimal angle
      -checking that IDF data exists at all
"""
class emnObj:
    def __init__(self, currentData, fname):
        self._emnData = currentData #save the emn data (list of strings)
        self.fileName = fname
        self.parts = self.getParts() #A list of part objects
        self.shapes = self.getShapes() #A list of shape objects
        self.errors = [] #A list of strings containing error messages
        self.units = self.getUnits() #A string with units (MM or THOU)
        self.drills = self.getDrills() #A list of drill objects

    def __str__(self):
        return self.fileName

   """
        Read through the placement section to get a list of parts to be placed.
        Part data is stored in "part" objects.
   """
    def getParts(self):
        partsRange = False
        currentPart = ""
        partList = []
        partLines = ["",""] 
        firstLine = True
        
        for line in self._emnData:
            if PLACEMENT_END in line:
                partsRange = False
            
            #grab every set of 2 lines in the placement section and make a part
            if partsRange:
                if firstLine: #the first line holds name and refdes
                    partLines[0] = line
                    firstLine = False
                else: #the second line holds position, side and orientation.
                    partLines[1] = line
                    partList.append(part(partLines))
                    firstLine = True
            
            #no useful data lives in the placement header
            if PLACEMENT_START in line:
                partsRange = True

        return partList

    """
        Read the file header and store the file units.
    """
    def getUnits(self):
        boardUnits = ""

        #read until you find units or the header ends
        for line in self._emnData:
            if "THOU" in line:
                boardUnits = "THOU"
                break
            elif "MM" in line:
                boardUnits = "MM"
                break
            else:
                boardUnits = "ERROR"

            if HEADER_END in line:
                self.errors.append("Could not find units in file")
                break

        return boardUnits

    """
        Read through the emn data and build shape objects for each shape.
    """
    def getShapes(self):
        shapeList = []
        currentLines = []
        coordRange = False

        for line in self._emnData: 
            #find shape starts
            for keyword in SHAPE_STARTS:
                if keyword in line:
                    coordRange = True
            
            #after a shape starts, start putting its data in a list
            if coordRange == True: 
                currentLines.append(line)
            
            #once a shape ends, make an object from its data
            for keyword in SHAPE_ENDS:
                if keyword in line:
                    shapeList.append(shape(currentLines))
                    currentLines = []
                    coordRange = False
        
        return shapeList

    """
        
    """
    def getDrills(self):
        drillList = []
        drillRange = False
        
        for line in self._emnData:
            if DRILL_END in line:
                drillRange = False
            if drillRange == True:
                drillList.append(drill(line))
            if DRILL_START in line:
                drillRange = True            

        return drillList

    #error checking suite
    def checkAllErrors(self, partsLibrary):
        self.checkHeightErrors()
        self.checkNegErrors()
        self.checkClosedErrors()
        self.checkRefDesErrors()
        self.checkRoundCutout()
        self.checkEmpty()
        self.checkArcAngle()
        if(partsLibrary):
            self.checkLibErrors(partsLibrary)

    #see if parts are in the library
    def checkLibErrors(self, partsLibrary):
        circFlag = False
        for part in self.parts:
            invCharFlag = False
            if ('_' in part.name) or ('^' in part.name) or ('_cc' in part.name):
                fmt = (part.name,part.refDes)
                self.errors.append(
                    "{0} ({1}) has invalid characters".format(fmt[0],fmt[1]) +
                    " in its part name.")
                invCharFlag = True
                circFlag = True
            if (part.name.upper() not in partsLibrary) and not invCharFlag:
                self.errors.append(part.name + " not found in parts library")

        if circFlag:
            self.errors.append("Part names with invalid characters were " +
                "detected. Please check CircuitWorks settings.")
            
        return

    #check for placement areas that are too short
    def checkHeightErrors(self):
        heightFlag = False
        for currentShape in self.shapes:
            heightError = False
            #print("h: " + currentShape.height)
            if ((currentShape.sType == PLACE_OUTLINE_START) and
                (self.units == "MM") and 
                (currentShape.height <= 0.026)):
                heightError = True
                heightFlag = True
            elif((currentShape.sType == PLACE_OUTLINE_START) and
                (self.units == "THOU") and 
                (currentShape.height <= 1)):
                heightError = True
                heightFlag = True
            if heightError:
                self.errors.append(currentShape.__str__() + 
                    " is too short to be checked in Board Modeler Lite.")
        if heightFlag:
            self.errors.append("Recommend using .PLACE_KEEPOUT instead" + 
                " of zero-height placement areas.")
                    
    def checkNegErrors(self):
        for currentShape in self.shapes:
            negShape = False
            for coordList in currentShape.coordinates:
                for coord in coordList:
                    if (coord[1] < 0) or (coord[2] < 0):
                        negShape = True
            if negShape:
                self.errors.append(currentShape.__str__() +
                    " has coordinates in negative X,Y space.")

        for currentPart in self.parts:
            if ((currentPart.coordinates[0] < 0) or 
                (currentPart.coordinates[1] < 0)):
                self.errors.append("Part " + currentPart.__str__() +
                    " is in negative X,Y space.")

        for currentDrill in self.drills:
            if ((currentDrill.coordinates[0] < 0) or 
                (currentDrill.coordinates[1] < 0)):
                self.errors.append(currentDrill.__str__() +
                    " is in negative X,Y space.")

    def checkClosedErrors(self):
        for currentShape in self.shapes:
            toCheck = []
            toCheck.append(currentShape.outline)
            if(currentShape.cutouts):
                for cutout in currentShape.cutouts:
                    toCheck.append(cutout)

            for s in toCheck:
                if (len(s) >= 3) and (s[0][:3] != s[-1][:3]):
                    if s[0][0] == 0:
                        self.errors.append(currentShape.__str__() + 
                            " is not a closed shape.")
                    else:
                        errStr = (currentShape.__str__() + 
                            " has a cutout at [%.2f,%.2f]" % 
                            (s[0][1],s[0][2]) + 
                            " that is not a closed shape.")
                        self.errors.append(errStr)
                elif (len(s) == 2) and (s[1][3] != 360):
                    self.errors.append(currentShape.__str__() + 
                            " is not a closed shape.")
    def checkRefDesErrors(self):
        for part in self.parts:
            if part.refDes[0] == "R":
                self.errors.append(part.__str__() + " has an \'R' " +
                    "reference designator.")

    def checkRoundCutout(self):
        toCheck = []
        for currentShape in self.shapes:
            toCheck = []
            if(currentShape.cutouts):
                for cutout in currentShape.cutouts:
                    toCheck.append(cutout)

        for s in toCheck:
            if(len(s) == 2) and (s[1][3] == 360):
                errStr = (currentShape.__str__() + 
                            " has a cutout at [%.2f,%.2f]" % 
                            (s[0][1],s[0][2]) + 
                            " that is circular.")
                self.errors.append(errStr)

    '''
    check for acute arc vertexes:
        this check looks at each end of a curve and determines whether
        its tangent forms an infinitesimal angle with the tangent of the
        next line or curve.
    '''
    def checkArcAngle(self):
        for currentShape in self.shapes:
            toCheck = []
            toCheck.append(currentShape.outline) #get shape outlines
            if(currentShape.cutouts):
                for cutout in currentShape.cutouts:
                    toCheck.append(cutout)  #and cutout outlines
            for s in toCheck:
                s = s[1:] #first/last point are equal, or you have other issues.
                if len(s) > 2: #any arc definition requires 3 points
                    for i in range(len(s)):
                        alpha0, alpha1 = 0,0  #angle from point 1 to point 0 or 2
                        beta0, beta1 = 0,0    #angle of tangent of each arc at point 1
                        phi0 = s[i-1][3]  #arc angle from point 0 to 1
                        phi1 = s[i][3]    #arc angle from point 1 to 2

                        #if we don't have any arcs, skip these
                        if phi0 or phi1:
                            phi0 = math.radians(phi0)
                            phi1 = math.radians(phi1)
                            
                            alpha0 = math.atan2(s[i-2][2]-s[i-1][2],
                                                s[i-2][1]-s[i-1][1])
                            alpha1 = math.atan2(s[i][2]-s[i-1][2],
                                                s[i][1]-s[i-1][1])

                            #get positive angles from negative angles from atan2
                            alpha0 = math.fmod((alpha0 + math.tau),math.tau)
                            alpha1 = math.fmod((alpha1 + math.tau),math.tau)

                            beta0 = alpha0 + (phi0/2)
                            beta1 = alpha1 - (phi1/2)

                            delta = math.fabs(beta1-beta0)
                            delta = math.fmod(delta,math.tau)

                            if math.isclose(delta,0,rel_tol=0.01,abs_tol=0.01) or \
                                math.isclose(delta,math.tau,rel_tol=0.01,abs_tol=0.01):
                                self.errors.append("Infinitesimal arc intersection" + 
                                                    " found at [%.2f,%.2f]" %
                                                    (s[i-1][1],s[i-1][2]))

    def checkEmpty(self):
        if not (self.shapes):
            self.errors.append("No shapes found. Is this IDF 3.0 data?")

    def checkCurves(self):
        pass

    def printAllErrors(self):
        if(self.errors):
            for line in self.errors:
                print(line)
            print("")
        else:
            print("No errors detected!\n")

#relevant shape data: type, outline, cutouts, height, layer (eventually)
class shape:
    def __init__(self, sData):
        self._sData = sData
        self.sType = sData[0].split()[0] 
        self.coordinates = self.getCoords() #list of list of all coordinates
        self.outline = self.coordinates[0] #list of ouline coordinates
        self.cutouts = self.coordinates[1:] #list of list of cutouts
        self.height = self.getHeight()
        self.layer = "" #not implementing this until we need it

    def __str__(self):
        info = (
            self.sType,self.outline[0][1],self.outline[0][2],
        )
        return "%s starting at [%.2f,%.2f]" % info

    #get shape outline
    def getCoords(self):
        shapeStrs = []  
        shapeOutline = []
        subshapeList = []
        currentSubshape = []
        cutoutIndex = 0

        for line in self._sData: #get shape lines
                #exploiting a convenient feature of IDF 3.0
                #that only/all coordinate lines are 4 fields long
                if len(line.split()) == 4: 
                    shapeStrs.append(line.split())

        #convert the strings to lists of floats
        for line in shapeStrs:
            cutout = float(line[0])
            xPos = float(line[1])
            yPos = float(line[2])
            arc = float(line[3])
            coord = [cutout,xPos,yPos,arc]
            if cutoutIndex == coord[0]:
                currentSubshape.append(coord)
            elif cutoutIndex != coord[0]:
                subshapeList.append(currentSubshape)
                currentSubshape = []
                currentSubshape.append(coord)
                cutoutIndex = coord[0]
        
        subshapeList.append(currentSubshape)
        return subshapeList

    #pull height/thickness from a shape
    def getHeight(self):
        sHeight = 0

        if self.sType == BOARD_START: #conditionals based on IDF 3.0 standard
            sHeight = float(self._sData[1])
        elif (self.sType == OTHER_START) or (self.sType == PLACE_OUTLINE_START):
            line = self._sData[1]
            sHeight = float(line.split()[1])

        return sHeight

#relevant part data: name, reference designator, coordinates, side
class part:
    def __init__(self, pData):
        self._pData = pData #a list of 2 strings
        self.coordinates = self.getCoords() #the part's position [x,y,rot]
        self.side = pData[1].split()[4] #the side of the board the part is on
        self.name, self.refDes = self.getNames() #the part's name

    def __str__(self):
        info = (
            self.name, self.refDes, self.coordinates[0], self.coordinates[1]
        )
        return "%s (%s) at [%.2f,%.2f]" % info

    def getCoords(self):
        xPos = float(self._pData[1].split()[0])
        yPos = float(self._pData[1].split()[1])
        rot  = float(self._pData[1].split()[3])
        return [xPos,yPos,rot]

    def getNames(self):
        pName = ""
        rName = ""

        if "\"" in self._pData[0]:
            pName = self._pData[0].split('\"')[1]
            rName = self._pData[0].split('\"')[-1]
            rName = rName.strip()
        else:
            pName = self._pData[0].split()[0]
            rName = self._pData[0].split()[-1]
        
        return pName, rName

#maybe drill could be a shape, but making another class was far easier
class drill:
    def __init__(self,dData):
        self._dData = dData
        dia = float(self._dData.split()[0])
        xPos = float(self._dData.split()[1])
        yPos = float(self._dData.split()[2])
        self.coordinates = [xPos,yPos]
        self.diameter = dia

    def __str__(self):
        info = (self.diameter,self.coordinates[0],self.coordinates[1])
        return "Drill with diameter %.2f at [%.2f,%.2f]" % info