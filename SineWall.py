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
from math import pi, sin,radians

class SineWall:
	def __init__(self, obj):
		obj.Proxy = self

		obj.addProperty("App::PropertyLinkSub", "Base", "Dimensions")

		obj.addProperty("App::PropertyFloat", "Amplitude", "Dimensions")
		obj.Amplitude=1

		obj.addProperty("App::PropertyFloat", "Wavelength", "Dimensions")
		obj.Wavelength=10

		obj.addProperty("App::PropertyFloat", "Phase", "Dimensions")
		obj.Phase=0

		obj.addProperty("App::PropertyInteger", "granularity", "Dimensions")
		obj.granularity=64
		self.aInc = 2*pi/obj.granularity

		obj.addProperty("App::PropertyBool", "debug", "Dimensions")
		obj.debug=False

		obj.addProperty("App::PropertyBool", "update", "Dimensions")
		obj.update=False

#	def onDocumentRestored(self, obj):
#		if (not hasattr(obj,"Reverse")):
#			obj.addProperty("App::PropertyBool", "Reverse", "Dimensions").Reverse=False
#		obj.ViewObject.Proxy.fp = obj

	def _ComputeOutVec(self,edge, param):
		P=edge.valueAt(param)
		vc = (self.cg-P).normalize()
		t = edge.tangentAt(param)
		hinge = t.cross(vc).normalize()
		return t.cross(hinge).normalize()

	def _ComputeSinglePoint(self,edge, param, amplitude):
		vec = self._ComputeOutVec(edge,param)
		P=edge.valueAt(param)
		return P+(vec*amplitude)

	def _ComputeEdge(self, obj, edge):
		start,end = edge.ParameterRange
		prange = end-start
		count = int(edge.Length/obj.Wavelength)
		count *= obj.granularity

		if not count:
			return [ edge.valueAt(start), edge.valueAt(end) ]
		pInc = prange/count

		def ComputeAval(i):
			return sin((i%obj.granularity)*self.aInc + 3*pi/2 + radians(obj.Phase))+1
						
		return [ self._ComputeSinglePoint(edge,start+(pInc*i), obj.Amplitude*ComputeAval(i)) for i in range(count)]

	def _compute(self, obj, edges):
		bs=Part.BSplineCurve()
		pts=[]
		for e in edges:
			pts.extend(self._ComputeEdge(obj, e))
		
		#dirty test
#		ptc=[Part.Vertex(p) for p in pts]
#		Part.show(Part.makeCompound(ptc))
		#end dirty test

		pts.append(pts[0])	# close the loop.
		bs = Part.BSplineCurve(pts)
		try:
			return bs.approximateBSpline(0.2,len(pts)//10,3,'C0') # caution, len(pts)/10 guessed empirically!
		except:
			return bs
		
	def _computeDiscreet(self, obj, edges):
		bss=[]
		for e in edges:
			pts=self._ComputeEdge(obj, e)
			pts.append(pts[0])	# close the curve
			bs=Part.BSplineCurve(pts)
			bss.append(bs.approximateBSpline(0.2, len(pts)//10, 3, 'C0'))	# caution, len(pts)/10 guessed empirically!
			
		return bss
		
	def _getEdges(self, obj):
		if not obj.Base[1]:
			self.discreet=False
			return obj.Base[0].Shape.Edges
			
		edges=[]
		shp=obj.Base[0].Shape
		for e in obj.Base[1]:
			if 'Edge' in e:
				self.discreet=True
				i=int(e[4:])-1
				edges.append(shp.Edges[i])
				
			elif 'InternalFace' in e:
				self.discreet=False
				i = int(e[12:])
				edges.extend( obj.Base[0].InternalShape.Faces[i].Edges)
				
			elif 'Face' in e:
				self.discreet=False
				i=int(e[4:])-1
				edges.extend( shp.Faces[i].Edges)

				
		return edges
		
	def execute(self, obj):
		if not obj.Base:	# not yet assigned.
			return

		self.aInc = 2*pi/obj.granularity

		self.cg = obj.Base[0].Shape.CenterOfGravity
		edges = self._getEdges(obj)
		
		if self.discreet:
			bss = self._computeDiscreet(obj, edges)
			c = Part.makeCompound([ bs.toShape() for bs in bss ])
			obj.Shape=c
		else:
			bs = self._compute(obj, edges)
			obj.Shape = bs.toShape()
			
#		obj.Placement=obj.Base[0].Placement
				
#		obj.Shape=computeShape(dia/2, drill/2, obj.Height, obj.RibCount, obj.BoreDepth, obj.invert, obj.debug)

	def onChanged(self, obj, name):
		if obj.update and name in ['Amplitude', 'Phase', 'Wavelength']:
			obj.recompute(True)
		
class ViewProviderSineWall:

	def __init__(self, obj):
		"""
		Set this object to the proxy object of the actual view provider
		"""

		obj.Proxy = self

	def attach(self, obj):
		"""
		Setup the scene sub-graph of the view provider, this method is mandatory
		"""
		self.fp = obj.Object
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
		if self.fp.Base:
			return [ self.fp.Base[0] ]
		return None

	def getIcon(self):
		"""
		Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
		"""

		return str(Path(__file__).parent / 'SineWall.svg')

	def dumps(self):
		"""
		Called during document saving.
		"""
		return None

	def loads(self,state):
		"""
		Called during document restore.
		"""

def _create(Base, name='SineWall'):
#	sel2 = FreeCADGui.Selection.getSelection()[0] 
#	print("sel2=",sel2)

	myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
	SineWall(myObj)
	myObj.Amplitude=1
	myObj.Wavelength=10
	myObj.Base = Base
	ViewProviderSineWall(myObj.ViewObject)
	myObj.recompute(True)
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

def create(name='SineWall'):
	sel2 = FreeCADGui.Selection.getSelectionEx() 

	for sel in sel2:
		print("sel=",sel)
		o=_create((sel.Object, sel.SubElementNames ), name)

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

	def CreateSineWall(name):
		App.ActiveDocument.openTransaction("Create SineWall")
		FreeCADGui.addModule("SineWall")
		FreeCADGui.doCommand("f = SineWall.create(name = '"+name+"')")
		FreeCADGui.doCommand("f = None")
		App.ActiveDocument.commitTransaction()

	class _CommandSineWall:
		"Command to create RibThread feature"
		def GetResources(self):
			return {'Pixmap'  : str(Path(__file__).parent / 'SineWall.svg'),
				'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_SineWall","SineWall"),
				'Accel': "",
				'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_SineWall","Create a line normal to the selected feature (generally a face or a closed planar edge)")
				}
		
		def Activated(self):
			CreateSineWall(name = "SineWall")
		    
		def IsActive(self):
			return True
			if App.ActiveDocument:
				return activeBody() is None
			else:
				return False
		    
	if App.GuiUp:
		FreeCADGui.addCommand('4Axis_SineWall', _CommandSineWall())
		print("Added Command")

	exportedCommands = ['4Axis_SineWall']
	print("I am SineWall!")
# -------------------------- /Gui command --------------------------------------------------

