#   Copyright (c) 2025 Steven James <pyro@4axisprinting.com>        
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
from math import pi, sin,cos, tan

#Deg30 = pi/6
#Deg60 = Deg30*2
#Sin60 = sin(Deg60)

def computeShape(Radius, Height, theta=2*pi/3):
	cyl = Part.makeCylinder(Radius, Height)

	sinval = sin(theta/2)
	base = cos(theta/2)*Radius
	tval = tan((pi-theta)/2)

	polypoints = [
		App.Vector(base, sinval*Radius,0),
		App.Vector(-base, sinval*Radius,0),
		App.Vector(0, sinval*Radius+tval*base, 0)
		]
	polypoints.append(polypoints[0])
	
	triWire = Part.makePolygon(polypoints)
	tri = Part.makeFace(triWire)
	tear = tri.extrude(Height * App.Vector(0,0,1))

	tear = tear.fuse(cyl)
	return tear

def getAttachedRadius(obj):
	try:
		e=obj.AttachmentSupport[0][1][0]
		o=obj.AttachmentSupport[0][0]
		i = int(e[4])
		return o.Geometry[i-1].Radius
	except:
		return 0
def deg2rad(angle):
	return angle*2*pi/360.0

class Teardrop:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Diameter", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Height", "Dimensions")


#	def onDocumentRestored(self, obj):
#		if (not hasattr(obj,"Reverse")):
#			obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
#		obj.ViewObject.Proxy.fp = obj

	def execute(self, obj):
		dia = obj.Diameter
		if not dia:
			dia=getAttachedRadius(obj)*2

		obj.Shape=computeShape(dia/2, obj.Height)

	def onChanged(self, obj, name):
		print("onChanged", name)
		
class ViewProviderTeardrop:

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
		return None

	def getIcon(self):
		"""
		Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
		"""

		return str(Path(__file__).parent / 'Teardrop.svg')

	def dumps(self):
		"""
		Called during document saving.
		"""
		return None

	def loads(self,state):
		"""
		Called during document restore.
		"""

def _create(name='Teardrop'):
#	sel2 = FreeCADGui.Selection.getSelection()[0] 
#	print("sel2=",sel2)

	myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
	Teardrop(myObj)
	myObj.Diameter=5
	myObj.Height=10
	ViewProviderTeardrop(myObj.ViewObject)
	App.ActiveDocument.recompute()
	return myObj


def attach(myObj, obj, mode='InertialCS', sub=''):
	print(f"{myObj}, {obj}, {sub}")
	myObj.addExtension('Part::AttachExtensionPython')
	myObj.AttacherEngine="Engine 3D"
	if sub:
		myObj.AttachmentSupport=[(obj,sub)]
	else:
		myObj.AttachmentSupport=obj
	myObj.MapMode=mode
	myObj.MapPathParameter=0
	myObj.AttachmentOffset.Rotation.Angle = pi/2

def create(name='Teardrop'):
	sel2 = FreeCADGui.Selection.getSelectionEx() 
	if not sel2:
		return _create(name=name)

	for sel in sel2:
		print("sel2=",sel)
		if sel.HasSubObjects:
			for s in sel.SubElementNames:
				o=_create(name)
				o.invert=True
				attach(o, sel.Object, sub=s)
				o.MapReversed=True
		else:
			if sel.Object.TypeId == 'Sketcher::SketchObject':
				for i in range( len(sel.Object.Geometry)):
					if sel.Object.Geometry[i].TypeId == 'Part::GeomCircle':
						o=_create(name=name)
						attach(o, sel.Object, sub=f"Edge{i+1}", mode="Concentric")
						o.Diameter=0	# so it will take the size of the circle
						o.MapReversed=True

#	_create(name=name)

# -------------------------- Gui command --------------------------------------------------

if "FCMacro" in __file__:
	create()
else:
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

	def CreateTeardrop(name):
		App.ActiveDocument.openTransaction("Create Teardrop")
		FreeCADGui.addModule("Teardrop")
		FreeCADGui.doCommand("f = Teardrop.create(name = '"+name+"')")
		FreeCADGui.doCommand("f = None")
		App.ActiveDocument.commitTransaction()

	class _CommandTeardrop:
		"Command to create Teardrop feature"
		def GetResources(self):
			return {'Pixmap'  : str(Path(__file__).parent / 'Teardrop.svg'),
				'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_Teardrop","Teardrop"),
				'Accel': "",
				'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_Teardrop","Create a line normal to the selected feature (generally a face or a closed planar edge)")
				}
		
		def Activated(self):
			CreateTeardrop(name = "Teardrop")
		    
		def IsActive(self):
			return True
			if App.ActiveDocument:
				return activeBody() is None
			else:
				return False
		    
	if App.GuiUp:
		FreeCADGui.addCommand('4Axis_Teardrop', _CommandTeardrop())
		print("Added Command")

	exportedCommands = ['4Axis_Teardrop']
	print("I am Teardrop!")
# -------------------------- /Gui command --------------------------------------------------

