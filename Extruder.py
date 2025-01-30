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

def computeShape(inshp, offset, length):
	shapes=[]
	for s in inshp.SubShapes:
		n = s.Faces[0].normalAt(1,1)	# get the normal for the shape
		try:
			ns = s.copy()	# make a copy
			ns.translate(n*offset)	#move it inward to the origin by 5mm
			shapes.append(ns.extrude(n*length))	# extrude it 10mm outward
		except:
			pass
		
#	return Part.makeSolid(Part.makeCompound(shapes))
	return Part.makeCompound(shapes)

class Extruder:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Offset", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Length", "Dimensions")
		obj.addProperty("App::PropertyLink", "Base", "Dimensions")
		obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False


	def onDocumentRestored(self, obj):
		if (not hasattr(obj,"Reverse")):
			obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
		obj.ViewObject.Proxy.fp = obj

	def execute(self, obj):
		print("Base=", obj.Base.Shape)
		obj.Shape=computeShape(obj.Base.Shape, obj.Offset, obj.Length)

	def onChanged(self, obj, name):
		print("onChanged", name)
		
class ViewProviderExtruder:

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

        App.Console.PrintMessage("Change property: " + str(prop) + "\n")

    def claimChildren(self):
        if hasattr(self,"fp"):
            return [ self.fp.Base ]
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        try:
            return str(Path(__file__).parent / 'Extruder.svg')
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

def create(name="Extruder"):
    sel2 = FreeCADGui.Selection.getSelection()[0] 
    print("sel2=",sel2)

    myObj = App.ActiveDocument.addObject("Part::FeaturePython", "Extruder")
    Extruder(myObj)
    myObj.Offset=-1
    myObj.Length=2
    myObj.Base=sel2
    ViewProviderExtruder(myObj.ViewObject)
    App.ActiveDocument.recompute()


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #Extruder is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreateExtruder(name):
    App.ActiveDocument.openTransaction("Create Extruder")
    FreeCADGui.addModule("Extruder")
    FreeCADGui.doCommand("f = Extruder.create(name = '"+name+"')")
#    FreeCADGui.doCommand("f.Base = FreeCADGui.Selection.getSelection()[0]")
#    FreeCADGui.doCommand("lattice2Executer.executeFeature(f)")
#    FreeCADGui.doCommand("f.Spine.ViewObject.hide()")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandExtruder:
    "Command to create Extruder feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'Extruder.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_Extruder","Extruder"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_Extruder","Extrude individual shapes in a compound shape")}
        
    def Activated(self):
        if len(FreeCADGui.Selection.getSelection()) == 1 :
            CreateExtruder(name = "Extruder")
        else:
            mb = QtGui.QMessageBox()
            mb.setIcon(mb.Icon.Warning)
            mb.setText(translate("4Axis_Extruder", "Select a shape that is a compound first!", None))
            mb.setWindowTitle(translate("4axis_Extruder","Bad selection", None))
            mb.exec_()
            
    def IsActive(self):
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_Extruder', _CommandExtruder())
    print("Added Command")

exportedCommands = ['4Axis_Extruder']
print("I am Extruder!")
# -------------------------- /Gui command --------------------------------------------------
