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

def computeRadial(v0, v1, line, angle):

	direction = v1.sub(v0)
	r=App.Rotation(App.Vector(0,0,1),direction)
	plDirection=App.Placement()
	plDirection.Rotation.Q = r.Q
	plDirection.Base = v0
	
	line.Placement = plDirection.multiply(App.Placement(App.Vector(0, 0, 0), App.Rotation(angle,0,0), App.Vector(0, 0, 0)))
	line.recompute()
#	FreeCAD.activeDocument().recompute([line])	# Necessary to actually instantiate line's position.
	return line.End


def MakeHelix(path, pitch, radius, cont=0, rotation=0, direction=1, join=False):
	PathDistance=path.Length*4/pitch	# 4 sample points per turn
	print("distance=",PathDistance)
	pathPoints = path.discretize(Distance=path.Length/PathDistance)
	print("pathPoints=", pathPoints)

	radialLine = Draft.makeWire([ App.Vector(0,0,0), App.Vector(radius, 0.0, 0.0)], closed=False, face=False, support=None)
	radialLine.Visibility=False
	radialPoints = []

	angle=rotation
	increment = 90*direction
	for i in range(len(pathPoints)-1):
		radialPoints.append( computeRadial(pathPoints[i], pathPoints[i+1], radialLine, angle) )
		angle = (angle+increment)%360
	if(cont):
		i = len(pathPoints)-2
		for x in range(cont):
			radialPoints.append( computeRadial(pathPoints[i], pathPoints[i+1], radialLine, angle) )
			angle = (angle+increment)%360

	arcs=[]
	for i in range(0,len(radialPoints),2):
		try:
			arcs.append(Part.Arc(radialPoints[i], radialPoints[i+1], radialPoints[i+2]))
		except:
			pass

	radialLine.Document.removeObject(radialLine.Name)

	if join:
		bs = [ a.toBSpline(a.FirstParameter, a.LastParameter) for a in arcs ]
		b = bs[0]
		[ b.join(e) for e in bs[1:] ]
		return b.toShape()

	print("points:", radialPoints)
	shp=Part.Shape(arcs)
	print(shp)
	print(shp.Edges)
	w = Part.Wire(shp.Edges)
	print("W=",w)

	return w

#sel = FreeCADGui.Selection.getSelectionEx()                 #0# Select an object or sub object
#subObject  = sel[0].SubObjects[0]
#print(sel[0].SubObjects)
#print( subObject, subObject.Length)
#print(type(subObject))
#if len(sel[0].SubObjects)>1:
#	subObject = Part.Wire(sel[0].SubObjects)


class PathHelix:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Radius", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Count", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Pitch", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Rotation", "Dimensions")
		obj.addProperty("App::PropertyLink", "Spine", "Dimensions")
		obj.addProperty("App::PropertyBool", "ExtraHalf", "Dimensions").ExtraHalf=False
		obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
		obj.addProperty("App::PropertyBool", "Join", "Dimensions").Join=True


	def onDocumentRestored(self, obj):
		if (not hasattr(obj,"Reverse")):
			obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
		obj.ViewObject.Proxy.fp = obj
		if (not hasattr(obj,"Join")):
			obj.addProperty("App::PropertyBool", "Join", "Dimensions").Join=False

	def execute(self, obj):
		print("Spine=", obj.Spine.Shape)
		w = MakeHelix(obj.Spine.Shape, obj.Pitch, obj.Radius, rotation=obj.Rotation, cont=2 if(obj.ExtraHalf) else 0, direction= -1 if(obj.Reverse) else 1, join=obj.Join)
#		w.Placement = obj.Placement
		obj.Shape=w
#		Part.show(obj.Shape)

	def onChanged(self, obj, name):
		l = obj.Spine.Shape.Length
		print("onChanged", name, l)
		if (name == "Count"):
			v=l/obj.Count
			if (not obj.Pitch == v):
				obj.Pitch = l/obj.Count
		elif (name == "Pitch"):
			v=l/obj.Pitch
			if (not obj.Count == v):
				obj.Count = l/obj.Pitch
		
class ViewProviderPathHelix:

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
        return "Wireframe"

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

        App.Console.PrintMessage("Change property: " + str(prop) + "\n")

    def claimChildren(self):
        if hasattr(self,"fp"):
            return [ self.fp.Spine ]
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        try:
            return str(Path(__file__).parent / 'PathHelix.svg')
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

#w = MakeHelix(subObject, 1, 3, cont=2)
#Part.show(w)

def create(name="PathHelix"):
    sel2 = FreeCADGui.Selection.getSelection()[0] 
    print("sel2=",sel2)

    myObj = App.ActiveDocument.addObject("Part::FeaturePython", "PathHelix")
    PathHelix(myObj)
    myObj.Radius=3
    myObj.Pitch=1
    myObj.Rotation=0
    myObj.Spine=sel2
    myObj.Count=sel2.Shape.Length
    ViewProviderPathHelix(myObj.ViewObject)
    App.ActiveDocument.recompute()


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore


def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreatePathHelix(name):
    App.ActiveDocument.openTransaction("Create PathHelix")
    FreeCADGui.addModule("PathHelix")
    FreeCADGui.doCommand("f = PathHelix.create(name = '"+name+"')")
#    FreeCADGui.doCommand("f.Base = FreeCADGui.Selection.getSelection()[0]")
#    FreeCADGui.doCommand("lattice2Executer.executeFeature(f)")
#    FreeCADGui.doCommand("f.Spine.ViewObject.hide()")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandPathHelix:
    "Command to create PathHelix feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'PathHelix.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_PathHelix","PathHelix"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_PathHelix","Create a Helix that follows a path")}
        
    def Activated(self):
        if len(FreeCADGui.Selection.getSelection()) == 1 :
            CreatePathHelix(name = "PathHelix")
        else:
            mb = QtGui.QMessageBox()
            mb.setIcon(mb.Icon.Warning)
            mb.setText(translate("4Axis_PathHelix", "Select a shape that is a compound whose children intersect, first!", None))
            mb.setWindowTitle(translate("4axis_PathHelix","Bad selection", None))
            mb.exec_()
            
    def IsActive(self):
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_PathHelix', _CommandPathHelix())
    print("Added Command")

exportedCommands = ['4Axis_PathHelix']

# -------------------------- /Gui command --------------------------------------------------
