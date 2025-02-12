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


class WireBinder:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyInteger", "Wire", "Dimensions").Wire=-1
		obj.addProperty("App::PropertyLinkList", "Base", "Dimensions")

	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
#		print(obj.Base)
		if obj.Wire==-1:
			obj.Shape = Part.makeCompound(obj.Base[0].Shape.Wires)
			m = obj.Base[0].Placement.Matrix.inverse()
			obj.Shape = obj.Shape.transformGeometry(m)
		else:
			obj.Shape = obj.Base[0].Shape.Wires[obj.Wire]

	def onChanged(self, obj, name):
		pass
#		print("onChanged", name)
		
class ViewProviderWireBinder:

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
            return str(Path(__file__).parent / 'WireBinder.svg')
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

def _create(obj, name="WireBinder"):
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
    WireBinder(myObj)
    myObj.Base= obj 
    myObj.Wire=-1
    ViewProviderWireBinder(myObj.ViewObject)
    App.ActiveDocument.recompute()
    return myObj

def create(name="WireBinder"):
    sel = FreeCADGui.Selection.getSelectionEx()[0]
    return _create(sel.Object, name=name)


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #WireBinder is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreateWireBinder(name):
    App.ActiveDocument.openTransaction("Create WireBinder")
    FreeCADGui.addModule("WireBinder")
    FreeCADGui.doCommand("f = WireBinder.create(name = '"+name+"')")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandWireBinder:
    "Command to create WireBinder feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'WireBinder.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_WireBinder","WireBinder"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_WireBinder","Extrude individual shapes in a compound shape")}
        
    def Activated(self):
        CreateWireBinder(name = "WireBinder")
            
    def IsActive(self):
        return True
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_WireBinder', _CommandWireBinder())
    print("Added Command")

exportedCommands = ['4Axis_WireBinder']
print("I am WireBinder!")
# -------------------------- /Gui command --------------------------------------------------
