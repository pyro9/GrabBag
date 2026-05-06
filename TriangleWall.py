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
from math import pi, sin,radians, asin

class TriangleWall:
	def __init__(self, obj):
		obj.Proxy = self

		obj.addProperty("App::PropertyLinkSub", "Base", "Dimensions")

		obj.addProperty("App::PropertyFloat", "Amplitude", "Dimensions")
		obj.Amplitude=1

		obj.addProperty("App::PropertyFloat", "Wavelength", "Dimensions")
		obj.Wavelength=10

		obj.addProperty("App::PropertyBool", "Phase", "Dimensions")
		obj.Phase=False

		obj.addProperty("App::PropertyBool", "CutCorners", "Dimensions").CutCorners=False
		obj.addProperty("App::PropertyBool", "AlternatePhase", "Dimensions").AlternatePhase=False

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

	def _ComputeSinglePoint(self,edge, param, face, amplitude):
		P=edge.valueAt(param)
		vec = self._ComputeOutVec(edge,param)
		if face.isInside(vec+P, 0.05, True):
			vec = -vec

		return P+(vec*amplitude)

	def tri(self,x):
		return 2* asin(sin(x)) /pi
			
		
	def _ComputeEdge(self, obj, edge, face, phase=-1):
		if phase<0:
			phase=obj.Phase
		start,end = edge.ParameterRange
		prange = end-start
		count = int( (edge.Length/obj.Wavelength) * 2 +0.001)

		if not count:
			return [ edge.valueAt(start), edge.valueAt(end) ]
		pInc = prange/count


		res=[]
		for i in range(count+1):
			if not i%2^phase:
				res.append(edge.valueAt(start+pInc*i))
			else:
				P = self._ComputeSinglePoint(edge, start+pInc*i, face, obj.Amplitude)
				res.append(P)
				
		if obj.CutCorners:
			P = edge.valueAt(start)
			if not P == res[0]:
				Q = [P]
				Q.extend(res)
				res = Q
				print(res)
			P = edge.valueAt(end)
			if not P == res[-1]:
				res.extend([P])

		return res

	def _compute(self, obj, edges):	# edges is a list of tuples ( edge, parent face of edge)
		phase = obj.Phase
		pts=[]
		for e,f in edges:
			p1 = self._ComputeEdge(obj, e,f, phase)
			if obj.AlternatePhase:
				phase = not phase
			if pts and (p1[0]-pts[-1]).Length > (p1[-1]-pts[-1]).Length:	# if the end of the new segment is closer than the beginning (The edge is reversed)
				p1.reverse()
			if pts and (p1[0]-pts[-1]).Length > (p1[0] - pts[0]).Length:	# if the first one is backward compared to the second one
				pts.reverse()
			pts.extend(p1)
		
		pts.append(pts[0])	# close the loop.

		return Part.makePolygon(pts)

		sh=[]
		prev=pts[0]
		for v in pts[1:]:
			sh.append(Part.makeLine(prev, v))
			prev=v

		c = Part.makeCompound(sh)
		return c
		
	def _computeDiscreet(self, obj, edges):
		bss=[]
		for e,f in edges:
			pts=self._ComputeEdge(obj, e,f)
#			pts.append(pts[0])	# close the curve
			bs=Part.makePolygon(pts)
			bss.append(bs)
			
		return bss
		
	def _edgeInFace(self, edge, face):
		for i in face.Edges:
			if edge.isSame(i):
				return True
		return False

	def _faceForEdge(self, edge, faces):
		for f in faces:
			if self._edgeInFace(edge, f):
				return f
		return None
	
	def _getEdges(self, obj):
		if not obj.Base[1]:
			edges=[]
			faces = Part.makeFace(obj.Base[0].Shape).Faces
			for e in obj.Base[0].Shape.Edges:
				edges.append( (e, self._faceForEdge(e, faces) ))
		
			self.discreet=False
			return edges
			
		edges=[]
		shp=obj.Base[0].Shape
#		faces = Part.makeFace(shp).Faces
		faces = shp.Faces
		print(faces)
		for element in obj.Base[1]:
			if 'Edge' in element:
				self.discreet=True
				i=int(element[4:])-1
				e = shp.Edges[i]
				f=self._faceForEdge(e,faces)
				if not f:
					raise Exception("Edges must be part of a face")
				edges.append( (e,f) )
				
			elif 'InternalFace' in element:
				self.discreet=False
				i = int(element[12:])-1
				f = obj.Base[0].InternalShape.Faces[i]
				# internal geometry doesn't get the Placement auto-applied, so we do it ourselves...
				f.transformShape(obj.Base[0].Placement.Matrix)
				for e in f.Edges:
					edges.append( (e,f) )
				
			elif 'Face' in element:
				self.discreet=False
				i=int(element[4:])-1
				f = shp.Faces[i]
				for e in f.Edges:
					edges.append( (e,f) )
				
		return edges
		
	def execute(self, obj):
		if not obj.Base:	# not yet assigned.
			return

		self.aInc = 2*pi/obj.granularity

		self.cg = obj.Base[0].Shape.CenterOfGravity
		edges = self._getEdges(obj)
		
		if self.discreet:
			bss = self._computeDiscreet(obj, edges)
			c = Part.makeCompound()
			print(type(c),c)
			obj.Shape=c
		else:
			obj.Shape = self._compute(obj, edges)
			
#		obj.Placement=obj.Base[0].Placement
#		obj.Shape=computeShape(dia/2, drill/2, obj.Height, obj.RibCount, obj.BoreDepth, obj.invert, obj.debug)

	def onChanged(self, obj, name):
		if obj.update and name in ['Amplitude', 'Phase', 'Wavelength']:
			obj.recompute(True)
		
class ViewProviderTriangleWall:

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

		return str(Path(__file__).parent / 'TriangleWall.svg')

	def dumps(self):
		"""
		Called during document saving.
		"""
		return None

	def loads(self,state):
		"""
		Called during document restore.
		"""

def _create(Base, name='TriangleWall'):
#	sel2 = FreeCADGui.Selection.getSelection()[0] 
#	print("sel2=",sel2)

	myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
	TriangleWall(myObj)
	myObj.Amplitude=1
	myObj.Wavelength=10
	myObj.Base = Base
	ViewProviderTriangleWall(myObj.ViewObject)
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

def create(name='TriangleWall'):
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

	def CreateTriangleWall(name):
		App.ActiveDocument.openTransaction("Create TriangleWall")
		FreeCADGui.addModule("TriangleWall")
		FreeCADGui.doCommand("f = TriangleWall.create(name = '"+name+"')")
		FreeCADGui.doCommand("f = None")
		App.ActiveDocument.commitTransaction()

	class _CommandTriangleWall:
		"Command to create RibThread feature"
		def GetResources(self):
			return {'Pixmap'  : str(Path(__file__).parent / 'TriangleWall.svg'),
				'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_TriangleWall","TriangleWall"),
				'Accel': "",
				'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_TriangleWall","Create a line normal to the selected feature (generally a face or a closed planar edge)")
				}
		
		def Activated(self):
			CreateTriangleWall(name = "TriangleWall")
		    
		def IsActive(self):
			return True
			if App.ActiveDocument:
				return activeBody() is None
			else:
				return False
		    
	if App.GuiUp:
		FreeCADGui.addCommand('4Axis_TriangleWall', _CommandTriangleWall())
		print("Added Command")

	exportedCommands = ['4Axis_TriangleWall']
	print("I am TriangleWall!")
# -------------------------- /Gui command --------------------------------------------------

