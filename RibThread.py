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
from math import pi, sin,cos

def getXYvec(theta, radius, offset=0):
	return App.Vector(cos(theta)*radius, sin(theta)*radius, offset)

def makeRibs(radius, height, arryRadius, count, offset=0):
	inc = 2*pi/count
	ribs = [ Part.makeCylinder(radius, height, getXYvec(inc*i, arryRadius, offset)) for i in range(count) ]

	return Part.makeCompound(ribs)

def computeShape(radius, DrillRadius, height, count, depth, invert=False, debug=False):
	ribRadius = radius-DrillRadius
	if invert and depth:
		ribs = makeRibs(ribRadius, height-depth, radius, count, depth)
	else:
		ribs = makeRibs(ribRadius, height-depth, radius, count)

	if invert:
		v = App.Vector(0,0,(depth))
		cone = Part.makeCone(radius, 0, 2*radius,v)
	else:
		v = App.Vector(0,0,(height-depth-2*radius))
		cone = Part.makeCone(0, radius, 2*radius, v)
	ribs = ribs.cut(cone)

	if debug:
		return Part.makeCompound([ribs, cone])

	cyl = Part.makeCylinder(radius, height)
	tool = cyl.cut(ribs)
	return tool

class RibThread:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyFloat", "Diameter", "Dimensions")
		obj.addProperty("App::PropertyFloat", "Height", "Dimensions")
		obj.addProperty("App::PropertyFloat", "DrillDiameter", "Dimensions")
		obj.addProperty("App::PropertyInteger", "RibCount", "Dimensions")
		obj.addProperty("App::PropertyFloat", "BoreDepth", "Dimensions")
		obj.addProperty("App::PropertyBool", "invert", "Dimensions")
		obj.addProperty("App::PropertyBool", "debug", "Dimensions")


#	def onDocumentRestored(self, obj):
#		if (not hasattr(obj,"Reverse")):
#			obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
#		obj.ViewObject.Proxy.fp = obj

	def execute(self, obj):
		obj.Shape=computeShape(obj.Diameter/2, obj.DrillDiameter/2, obj.Height, obj.RibCount, obj.BoreDepth, obj.invert, obj.debug)

	def onChanged(self, obj, name):
		print("onChanged", name)
		
class ViewProviderRibThread:

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

		return str(Path(__file__).parent / 'RibThread.svg')

	def dumps(self):
		"""
		Called during document saving.
		"""
		return None

	def loads(self,state):
		"""
		Called during document restore.
		"""

def create(name='RibThread'):
#	sel2 = FreeCADGui.Selection.getSelection()[0] 
#	print("sel2=",sel2)

	myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
	RibThread(myObj)
	myObj.Diameter=5
	myObj.DrillDiameter=4.5
	myObj.Height=10
	myObj.RibCount=3
	myObj.BoreDepth = 1
	ViewProviderRibThread(myObj.ViewObject)
	App.ActiveDocument.recompute()


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

	def CreateRibThread(name):
		App.ActiveDocument.openTransaction("Create RibThread")
		FreeCADGui.addModule("RibThread")
		FreeCADGui.doCommand("f = RibThread.create(name = '"+name+"')")
		FreeCADGui.doCommand("f = None")
		App.ActiveDocument.commitTransaction()

	class _CommandRibThread:
		"Command to create RibThread feature"
		def GetResources(self):
			return {'Pixmap'  : str(Path(__file__).parent / 'RibThread.svg'),
				'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_RibThread","RibThread"),
				'Accel': "",
				'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_RibThread","Create a line normal to the selected feature (generally a face or a closed planar edge)")
				}
		
		def Activated(self):
			CreateRibThread(name = "RibThread")
		    
		def IsActive(self):
			return True
			if App.ActiveDocument:
				return activeBody() is None
			else:
				return False
		    
	if App.GuiUp:
		FreeCADGui.addCommand('4Axis_RibThread', _CommandRibThread())
		print("Added Command")

	exportedCommands = ['4Axis_RibThread']
	print("I am RibThread!")
# -------------------------- /Gui command --------------------------------------------------

