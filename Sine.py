#   Copyright (c) 2024 Steven James <pyro@4axisprinting.com>        
#                                                                         
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Library General Public
#   License as published by the Free Software Foundation; either
#   version 2 of the License, or (at your option) any later version.
#
#   This library  is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Library General Public License for more details.
#
#   You should have received a copy of the GNU Library General Public
#   License along with this library; see the file COPYING.LIB. If not,
#   write to the Free Software Foundation, Inc., 59 Temple Place,
#   Suite 330, Boston, MA  02111-1307, USA
#                                                                         

import Draft, Part, FreeCADGui
import FreeCAD as App
import os
from pathlib import Path
import math

def computeRadialTangent(normal, vertex, center, angle):
	radial = vertex.Point - center
	radial.normalize()

	tangent = radial.cross(abs(normal))

	rot = App.Rotation(tangent, angle)
	ret=rot.multVec(normal)
	return ret

def computeShapeSpherical(radius, magnitude, frequency, phase, num):
	vtcs=[]

	delta = 2*math.pi/num

	for i in range(num):
		theta=i*delta

		Ztheta = math.sin((theta+phase)*frequency)*magnitude
		z = math.sin(Ztheta)*radius
		rad = math.cos(Ztheta)*radius
		x=math.cos(theta)*rad
		y=math.sin(theta)*rad

		vtcs.append(App.Vector(x,y,z))

	print(vtcs)

	if True:
		spline=Part.BSplineCurve()
		spline.interpolate(vtcs, PeriodicFlag=True)
		shp=spline.toShape()
	else:
		shp = Part.makeCompound(vtcs)

	return shp

def computeShape(radius, magnitude, frequency, phase, num, phi=0):
	vtcs=[]

	delta = 2*math.pi/num

	for i in range(num):
		theta=i*delta
		z = math.sin((theta+phase)*frequency)*magnitude
		x=math.cos(theta)*radius
		y=math.sin(theta)*radius

		if phi:
			vec = computeRadialTangent(App.Vector(0,0,z), Part.Vertex(x,y,0) , App.Vector(0,0,0), phi)
			vtcs.append( App.Vector(x,y,0) + vec)
		else:
			vtcs.append(App.Vector(x,y,z))

	print(vtcs)

	spline=Part.BSplineCurve()
	spline.interpolate(vtcs, PeriodicFlag=True)
	shp=spline.toShape()

	return shp
	


class Sine:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Radius", "Dimensions").Radius=10
		obj.addProperty("App::PropertyFloat", "Amplitude", "Dimensions").Amplitude=10
		obj.addProperty("App::PropertyFloat", "Frequency", "Dimensions").Frequency=2
		obj.addProperty("App::PropertyFloat", "Phase", "Dimensions").Phase=0
		obj.addProperty("App::PropertyFloat", "Phi", "Dimensions").Phi=0
		obj.addProperty("App::PropertyInteger", "Num", "Dimensions").Num=180
		
		obj.addProperty("App::PropertyEnumeration", "Type", "Dimensions").Type= ['Circular', 'Spherical']
		obj.Type='Circular'


	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		if obj.Type == 'Circular':
			obj.Shape=computeShape(obj.Radius, obj.Amplitude, obj.Frequency, obj.Phase, obj.Num, obj.Phi)
		else:
			obj.Shape=computeShapeSpherical(obj.Radius, obj.Amplitude, obj.Frequency, obj.Phase, obj.Num)

	def onChanged(self, obj, name):
		pass
#		print("onChanged", name)
		
class ViewProviderSine:

    def __init__(self, obj):
        """
        Set this object to the proxy object of the actual view provider
        """

        obj.Proxy = self
        self.fp = obj.Object

    def attach(self, obj):
        """
        Setup the scene sub-graph of the view provider, this method is mandatory
        """
        return

    def updateData(self, fp, prop):
        """
        If a property of the handled feature has changed we have the chance to handle this here
        """
        return

    def getDisplayModes(self,obj):
        """
        Return a list of display modes.
        """
        return []

    def getDefaultDisplayMode(self):
        """
        Return the name of the default display mode. It must be defined in getDisplayModes.
        """
        return "Flat Lines"

    def setDisplayMode(self,mode):
        """
        Map the display mode defined in attach with those defined in getDisplayModes.
        Since they have the same names nothing needs to be done.
        This method is optional.
        """
        return mode

    def onChanged(self, vp, prop):
        """
        Print the name of the property that has changed
        """

#        App.Console.PrintMessage("Change property: " + str(prop) + "\n")

    def claimChildren(self):
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        try:
            return str(Path(__file__).parent / 'Sine.svg')
        except:
            print("Fallback to xpm")
            return """
                /* XPM */
                static char *drawing[] = {
                /* columns rows colors chars-per-pixel */
                "16 16 4 1 ",
                "  c #D27671",
                ". c None",
                "X c #D1AE9B",
                "o c #939B61",
                /* pixels */
                "....  ..........",
                "...X.XX.........",
                "... .X..........",
                "o oo. ..........",
                ".X .Xo..........",
                "XXX.XXo.X   ....",
                ". ..X..oX.. ....",
                	".... X .o.X.....",
                	"....XX...o......",
                	"........ o......",
                	"....... ..X.....",
                	"......X   oXX X.",
                	"..........o.X ..",
                	"...........oX...",
                	".........X X....",
                	"........XX.X....",
                	};
                 """


    def dumps(self):
        """
        Called during document saving.
        """
        return None

    def loads(self,state):
        """
        Called during document restore.
        """

def create(name="Sine"):
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
    Sine(myObj)
    ViewProviderSine(myObj.ViewObject)
    App.ActiveDocument.recompute()


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #Sine is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreateSine(name):
    App.ActiveDocument.openTransaction("Create Sine")
    FreeCADGui.addModule("Sine")
    FreeCADGui.doCommand("f = Sine.create(name = '"+name+"')")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandSine:
    "Command to create Sine feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'Sine.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_Sine","Sine"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_Sine","Extrude individual shapes in a compound shape")}
        
    def Activated(self):
        CreateSine(name = "Sine")
            
    def IsActive(self):
        return True
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_Sine', _CommandSine())
    print("Added Command")

exportedCommands = ['4Axis_Sine']
print("I am Sine!")
# -------------------------- /Gui command --------------------------------------------------
