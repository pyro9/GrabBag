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

def fixPlacement(s,p):
	s.Placement=p
	return s

def EdgeToBiArcs(Edge, tolerance=0.01):
	l = Edge.Curve.toBiArcs(tolerance)
	return Part.makeCompound(l)

class ToBiArcs:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyLinkList", "Base", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Tolerance", "Dimensions").Tolerance=0.01

	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		c = [ EdgeToBiArcs(e,obj.Tolerance) for e in obj.Base[0].Shape.Edges ]
		if len(c)>1:
			c = Part.makeCompound(c)
		else:
			c=c[0]

		obj.Shape=c
		return

	def onChanged(self, obj, name):
		pass
#		print("onChanged", name)
		
class ViewProviderToBiArcs:

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

        return str(Path(__file__).parent / 'ToBiArcs.svg')


    def dumps(self):
        """
        Called during document saving.
        """
        return None

    def loads(self,state):
        """
        Called during document restore.
        """

def attach(myObj, obj):
    myObj.addExtension('Part::AttachExtensionPython')
    myObj.AttacherEngine="Engine 3D"
    myObj.MapMode="ObjectXY"
    myObj.AttachmentSupport=obj
    myObj.MapPathParameter=0

def _create(obj, name="ToBiArcs"):
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
    ToBiArcs(myObj)
    myObj.Base= obj 
    ViewProviderToBiArcs(myObj.ViewObject)
    App.ActiveDocument.recompute()
    return myObj

def create(name="ToBiArcs"):
    sel = FreeCADGui.Selection.getSelectionEx()[0]
    return _create(sel.Object, name=name)

if "FCMacro" in __file__:
	create()
else:

# -------------------------- Gui command --------------------------------------------------

    from PySide import QtCore
    from PySide import QtGui

    def translate(context, text, disambig):
        #ToBiArcs is not translatable, sorry...
        return text

    def activeBody():
        if App.ActiveDocument is None: return None
        if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
            return None
        return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

    def CreateToBiArcs(name):
        App.ActiveDocument.openTransaction("Create ToBiArcs")
        FreeCADGui.addModule("ToBiArcs")
        FreeCADGui.doCommand("f = ToBiArcs.create(name = '"+name+"')")
        FreeCADGui.doCommand("f = None")
        App.ActiveDocument.commitTransaction()

    class _CommandToBiArcs:
        "Command to create ToBiArcs feature"
        def GetResources(self):
            return {'Pixmap'  : str(Path(__file__).parent / 'ToBiArcs.svg'),
                    'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_ToBiArcs","ToBiArcs"),
                    'Accel': "",
                    'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_ToBiArcs","Extrude individual shapes in a compound shape")}
        
        def Activated(self):
            CreateToBiArcs(name = "ToBiArcs")
            
        def IsActive(self):
            return True
            if App.ActiveDocument:
                return activeBody() is None
            else:
                return False
            
    if App.GuiUp:
        FreeCADGui.addCommand('4Axis_ToBiArcs', _CommandToBiArcs())
        print("Added Command")

    exportedCommands = ['4Axis_ToBiArcs']
    print("I am ToBiArcs!")
    # -------------------------- /Gui command --------------------------------------------------
