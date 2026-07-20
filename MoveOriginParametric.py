#   Copyright (c) 2026 Steven James <pyro@4axisprinting.com>        
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
from math import acos

def Center(shp):
	(x1,x2,y1,y2) = shp.ParameterRange
	x=(x2-x1)/2 + x1
	y=(y2-y1)/2 + y1
	return x,y

def computeRotationMatrix(f, flip=False):
	if flip:
		v=App.Vector(0,0,1)
	else:
		v=App.Vector(0,0,-1)

	n=f.normalAt(*Center(f))

	r=App.Rotation(n.cross(v), Radian=acos(n*v)) #given the axis of rotation and the angle, use App.Rotation to compute the matrix that created that rotationm

	return r.toMatrix()

def computeMoveMatrix(shp):
	tm = App.Matrix()
	tm.move(shp.CenterOfGravity)

	return tm.inverse()

def computeTransformMatrix(f):
	return computeRotationMatrix(f)*computeMoveMatrix(f)

class MoveOriginParametric:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyLinkSubList", "Support", "Base")
		obj.addProperty("App::PropertyBool", "Internal", "Base")
		obj.addProperty("App::PropertyBool", "IgnorePlacement", "Base")
		obj.addProperty("App::PropertyBool", "Flip", "Base")
		obj.addProperty("App::PropertyInteger", "Face", "Dimensions")

		obj.IgnorePlacement=False
		obj.Flip=False

	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		subject,subel = obj.Support[0]
		f=obj.Face

		if f>=0:
			tm = computeMoveMatrix(subject.Shape.Faces[f])
			rm = computeRotationMatrix(subject.Shape.Faces[f], flip=obj.Flip)
			m = rm*tm	# NOTE: rotation matrix MUST come first
		else:
			m = computeMoveMatrix(subject.Shape)

		pm = subject.Placement.Matrix
		s = subject.Shape.copy()
		s.Placement = App.Placement()	# a new 0 placement
		s = s.transformGeometry(m)

		obj.Shape = s
		if not obj.IgnorePlacement:
			obj.Placement.Matrix=pm*m.inverse()
		
#		if self.Internal:
#			f = obj.Base.InternalShape.Faces[obj.Face]
#			f.transformShape( obj.Base.Placement.Matrix)
#		else:
#			f = obj.Base.Shape.Faces[obj.Face]

	def onChanged(self, obj, name):
		print("onChanged", name)
		
class ViewProviderMoveOriginParametric:

    def __init__(self, obj):
        """
        Set this object to the proxy object of the actual view provider
        """

        obj.Proxy = self

    def attach(self, obj):
        self.fp = obj.Object
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
            subject,subel = self.fp.Support[0]
            return [ subject ]
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        try:
            return str(Path(__file__).parent / 'MoveOriginParametric.svg')
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

def create(name="MoveOriginParametric"):
    sel2 = FreeCADGui.Selection.getSelectionEx()[0] 
    print("sel2=",sel2)
    createMoveOriginParametric(sel2.Object, sel2.SubElementNames, name)

def createMoveOriginParametric(Object, SubElementNames, Name="MoveOriginParametric"):
    """
    _createMoveOriginParametric(Object, SubElementNames, Name="MoveOriginParametric")
    """
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", Name)
    MoveOriginParametric(myObj)
    myObj.Support=(Object, SubElementNames)

    if SubElementNames and 'Face' in SubElementNames[0]:
        myObj.Face = int(SubElementNames[0][4:])-1
    else:
        myObj.Face = -1

#    if 'Internal' in sel2.SubElementNames[0]:
#        myObj.Proxy.Internal=True
#        myObj.Face = int(sel2.SubElementNames[0][12:])-1
#    else:
#        myObj.Face = int(sel2.SubElementNames[0][4:])-1
    ViewProviderMoveOriginParametric(myObj.ViewObject)
    App.ActiveDocument.recompute()


# -------------------------- Gui command --------------------------------------------------

from PySide import QtCore
from PySide import QtGui

def translate(context, text, disambig):
    #MoveOriginParametric is not translatable, sorry...
    return text

def activeBody():
    if App.ActiveDocument is None: return None
    if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
        return None
    return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

def CreateMoveOriginParametric(name):
    App.ActiveDocument.openTransaction("Create MoveOriginParametric")
    FreeCADGui.addModule("MoveOriginParametric")
    FreeCADGui.doCommand("f = MoveOriginParametric.create(name = '"+name+"')")
#    FreeCADGui.doCommand("f.Base = FreeCADGui.Selection.getSelection()[0]")
#    FreeCADGui.doCommand("lattice2Executer.executeFeature(f)")
#    FreeCADGui.doCommand("f.Spine.ViewObject.hide()")
    FreeCADGui.doCommand("f = None")
    App.ActiveDocument.commitTransaction()

class _CommandMoveOriginParametric:
    "Command to create MoveOriginParametric feature"
    def GetResources(self):
        return {'Pixmap'  : str(Path(__file__).parent / 'MoveOriginParametric.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_MoveOriginParametric","MoveOriginParametric"),
                'Accel': "",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_MoveOriginParametric","Extrude individual shapes in a compound shape")}
        
    def Activated(self):
        if len(FreeCADGui.Selection.getSelection()) == 1 :
            CreateMoveOriginParametric(name = "MoveOriginParametric")
        else:
            mb = QtGui.QMessageBox()
            mb.setIcon(mb.Icon.Warning)
            mb.setText(translate("4Axis_MoveOriginParametric", "Select a shape that is a compound first!", None))
            mb.setWindowTitle(translate("4axis_MoveOriginParametric","Bad selection", None))
            mb.exec_()
            
    def IsActive(self):
        if App.ActiveDocument:
            return activeBody() is None
        else:
            return False
            
if App.GuiUp:
    FreeCADGui.addCommand('4Axis_MoveOriginParametric', _CommandMoveOriginParametric())
    print("Added Command")

exportedCommands = ['4Axis_MoveOriginParametric']
print("I am MoveOriginParametric!")
# -------------------------- /Gui command --------------------------------------------------
