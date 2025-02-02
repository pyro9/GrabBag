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

def computeRadialTangent(normal, vertex, center, angle):
	radial = vertex.Point - center
	radial.normalize()

	tangent = radial.cross(normal)

	rot = App.Rotation(tangent, angle)
	return rot.multVec(normal)


def computeShape(Object, sub, length, reverse=False, angle=0):
	f=None
	norm=None
	v=None
	if "Edge" in sub:
		ix = int(sub[4:])
		edge= Object.Shape.Edges[ix-1]
		f=Part.makeFace(edge)
		norm = f.normalAt(1,1)
		v = Part.Vertex(f.CenterOfMass)
	if "Face" in sub:
		ix = int(sub[4:])
		f = Object.Shape.Faces[ix-1]
		norm = f.normalAt(1,1)
		v = Part.Vertex(f.CenterOfMass)

	if "Vertex" in sub:
		ix=int(sub[6:])
		v = Object.Shape.Vertexes[ix-1]
		p = Object.Shape.findPlane()
		norm = p.normal(1,1)
		if(angle):
			norm = computeRadialTangent(norm, v, Object.Shape.CenterOfGravity, angle)

	if not norm or not v:
		return None

	if reverse:
		length = -length

	ex = v.extrude(norm*length)

	return ex

class NormalLine:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Length", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Angle", "Dimensions").Angle=0
		obj.addProperty("App::PropertyLinkSubList", "Base", "Dimensions")
		obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False


	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		print(obj.Base)
		o=obj.Base[0][0]
		sub=obj.Base[0][1][0]
		obj.Shape=computeShape(o, sub, obj.Length, obj.Reverse, obj.Angle)

	def onChanged(self, obj, name):
		pass
#		print("onChanged", name)
		
class ViewProviderNormalLine:

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
        if hasattr(self,"fp"):
            return [ self.fp.Base ]
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        try:
            return str(Path(__file__).parent / 'NormalLine.svg')
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

def _create(obj, element, name="NormalLine"):
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", "NormalLine")
    NormalLine(myObj)
    myObj.Length=10
    myObj.Base=(obj, (element))
    ViewProviderNormalLine(myObj.ViewObject)
    App.ActiveDocument.recompute()

def expandSelection(sel):
	for s in sel:
		for e in s.SubElementNames:
			yield (s.Object, e)

def create(name=NormalLine):
    for (o,s) in expandSelection(FreeCADGui.Selection.getSelectionEx()):
        _create(o,s,name)


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #NormalLine is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreateNormalLine(name):
    App.ActiveDocument.openTransaction("Create NormalLine")
    FreeCADGui.addModule("NormalLine")
    FreeCADGui.doCommand("f = NormalLine.create(name = '"+name+"')")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandNormalLine:
    "Command to create NormalLine feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'NormalLine.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_NormalLine","NormalLine"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_NormalLine","Extrude individual shapes in a compound shape")}
        
    def Activated(self):
        CreateNormalLine(name = "NormalLine")
            
    def IsActive(self):
        return True
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_NormalLine', _CommandNormalLine())
    print("Added Command")

exportedCommands = ['4Axis_NormalLine']
print("I am NormalLine!")
# -------------------------- /Gui command --------------------------------------------------
