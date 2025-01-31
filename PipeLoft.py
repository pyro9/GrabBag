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

def getFace(sublink):
	idx = int(sublink[1][4:])
	return sublink[0].Shape.Faces[idx-1]

def makePipeShape(From, To, UnTwist):
	wf=getFace(From).SubShapes
	wt=getFace(To).SubShapes	

	length = min(len(wf), len(wt))

	l=[]
	for i in range(length):
		p = Part.makeLoft([wf[i],wt[i]],solid=True)
		l.append(p)

	p = l[0].cut(l[1:])
	return p

class PipeLoft:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyLinkSubList", "Base", "Dimensions")
		obj.addProperty("App::PropertyBool", "UnTwist", "Dimensions").UnTwist=False


	def onDocumentRestored(self, obj):
		if (not hasattr(obj,"UnTwist")):
			obj.addProperty("App::PropertyBool", "UnTwist", "Dimensions").UnTwist=False
		obj.ViewObject.Proxy.fp = obj

	def execute(self, obj):
		From=(obj.Base[0][0],obj.Base[0][1][0])
		To=(obj.Base[1][0],obj.Base[1][1][0])
		obj.Shape = makePipeShape(From,To, obj.UnTwist)

	def onChanged(self, obj, name):
		print("onChanged", name)
		
class ViewProviderPipeLoft:

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
            return str(Path(__file__).parent / 'PipeLoft.svg')
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

def create(name="PipeLoft"):
    sel2 = FreeCADGui.Selection.getSelectionEx()
    print("sel2=",sel2)

    myObj = App.ActiveDocument.addObject("Part::FeaturePython", "PipeLoft")
    PipeLoft(myObj)

    myObj.Base = [ (sel2[0].Object, (sel2[0].SubElementNames[0])), (sel2[1].Object, (sel2[1].SubElementNames[0]))]
    ViewProviderPipeLoft(myObj.ViewObject)
    App.ActiveDocument.recompute()


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #PipeLoft is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreatePipeLoft(name):
    App.ActiveDocument.openTransaction("Create PipeLoft")
    FreeCADGui.addModule("PipeLoft")
    FreeCADGui.doCommand("f = PipeLoft.create(name = '"+name+"')")
#    FreeCADGui.doCommand("f.Base = FreeCADGui.Selection.getSelection()[0]")
#    FreeCADGui.doCommand("lattice2Executer.executeFeature(f)")
#    FreeCADGui.doCommand("f.Spine.ViewObject.hide()")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandPipeLoft:
    "Command to create PipeLoft feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'PipeLoft.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_PipeLoft","PipeLoft"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_PipeLoft","Create a loft between 2 pipe-like faces")}
        
    def Activated(self):
        if len(FreeCADGui.Selection.getSelection()) == 2 :
            CreatePipeLoft(name = "PipeLoft")
        else:
            mb = QtGui.QMessageBox()
            mb.setIcon(mb.Icon.Warning)
            mb.setText(translate("4Axis_PipeLoft", "Select two faces first!", None))
            mb.setWindowTitle(translate("4axis_PipeLoft","Bad selection", None))
            mb.exec_()
            
    def IsActive(self):
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_PipeLoft', _CommandPipeLoft())
    print("Added Command")

exportedCommands = ['4Axis_PipeLoft']
print("I am PipeLoft!")
# -------------------------- /Gui command --------------------------------------------------
