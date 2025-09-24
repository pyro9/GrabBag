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

def EdgeToBiArcs(Edge, tolerance=0.01):
	if type(Edge.Curve) in [ Part.Line, Part.Circle ]:
		l=  Edge.Curve.toNurbs(Edge.FirstParameter,Edge.LastParameter)
		l = l.toBiArcs(tolerance)
	else:
		l = Edge.Curve.toBiArcs(tolerance)
	return l

def makeCumulative(l):
	acc=0

	for i in l:
		acc+=i
		yield acc
		
def forceRange(val, rnge):
	while val<0:
		val+=rnge
	while val >= rnge:
		val -= rnge

	return val

def joinEdges(l):
	if not l:
		return None
	if len(l)==1:
		return l[0]

	c = [ e.Curve.toBSpline(e.FirstParameter, e.LastParameter) for e in l ]
	r = c[0]
	res = [ r.join(i) for i in c[1:] ]
	if False in res:
		return False

	return r.toShape()

def moveStart(e,d):
	p=e.getParameterByLength(d)
	el = e.split(p).Edges
	el = [ e.reversed() for e in el]
	s=joinEdges(el)
	return s.Edge1

def getRad(c):
	if type(c) in [Part.Circle, Part.ArcOfCircle]:
		return c.Radius
	else:
		return 1000000

def getStartDistances(l):
	acc=0

	for e in l:
		yield(acc)
		acc+= e.length()

def getLength(l):
	acc=0
	for e in l:
		acc+=e.length()
	return acc

def getRadii(edge, tr, tolerance=0.01):
	"""
	given an edge and a radius threshold, return a list of
	distances where the radius is smallest.
	"""
	c = EdgeToBiArcs(edge,tolerance) # c, a list of all biArcs

	active=False
	regions=[]
	i=j=k=0
	for k,e in enumerate(c):
		if getRad(e) <tr:
			if not active:
				i=k
				active=True
		else:
			if active:
				j=k
				regions.append( (i,j) )
				active = False

	dists = [ i for i in getStartDistances(c) ]	# a corresponding list of all distances from the start of the edge

	distances=[]
	for i,j in regions:
		l = getLength(c[i:j])
		distances.append(l/2 + dists[i])

	return distances

class Recompose:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyLinkList", "Base", "Base")
		obj.addProperty("App::PropertyBool", "ClaimChildren", "Dimensions").ClaimChildren=True
		obj.addProperty("App::PropertyFloatConstraint", "Tolerance", "Dimensions").Tolerance=(0.01, 0.0, 1000.0, 0.01)
		obj.addProperty("App::PropertyFloatConstraint", "Start", "Dimensions").Start=(0.0, 0.0, 1000.0, 0.1)

		obj.addProperty("App::PropertyEnumeration", "Mode", "Base").Mode=['Nothing', 'Just Join', 'Split by Distance', 'Split by Radii']
		obj.Mode=1

		obj.addProperty("App::PropertyFloatList", "SplitDistances", "Distance").SplitDistances=[ ]
		obj.addProperty("App::PropertyFloatConstraint", "SplitDistance", "Distance").SplitDistance= (0.0, 0.0, 100000000000, 0.1)	# value, min, max, step
		obj.addProperty("App::PropertyBool", "AddDistance", "Distance").AddDistance=False
		obj.addProperty("App::PropertyFloatConstraint", "Threshold", "Radius").Threshold=( 0.0, 0.0, 10000.0, 0.1)
		obj.addProperty("App::PropertyFloatList", "RadiusSplits", "Radius").RadiusSplits=[]

	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		s = joinEdges( obj.Base[0].Shape.Edges)
		if not s:
			raise Exception("{obj.Name}:Can't join")

		if obj.Start:
			e=moveStart(s.Edge1, obj.Start)
		else:
			e=s.Edge1

		if obj.SplitDistance:
			p = [e.getParameterByLength(obj.SplitDistance)]
		else:
			p=[]

		if obj.SplitDistances:
			params = [ e.getParameterByLength(i) for i in obj.SplitDistances ]
			p = p + params

		if obj.Threshold:
			obj.RadiusSplits = getRadii(e, obj.Threshold)
			params = [ e.getParameterByLength(i) for i in obj.RadiusSplits ]
			p = p + params
			print("params=", params)

		p = list(set(p))
		w = e.split(p)
		print("w=", w)
		obj.Shape = w

	def onChanged(self, obj, name):
		if name == 'AddDistance':
			if obj.AddDistance:
				l=obj.SplitDistances
				l.append(obj.SplitDistance)
				obj.SplitDistances = l
				obj.AddDistance=False
#				print("Added")
		if name == 'SplitDistance':	# keep SplitDistance between 0 and the length of the Base edge
			v = forceRange(obj.SplitDistance,obj.Base[0].Shape.Length)
			if obj.SplitDistance != v:
				obj.SplitDistance = v
		if name == 'Start':	# keep SplitDistance between 0 and the length of the Base edge
			v = forceRange(obj.Start,obj.Base[0].Shape.Length)
			if obj.Start != v:
				obj.Start = v

		if name in ['Start', 'Threshold', 'Tolerance', 'SplitDistance']:
			obj.recompute(False)
		pass
#		print("onChanged", name)
		
class ViewProviderRecompose:

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

    def doubleClicked(self, obj):
        print("doubleClicked\n")
        return True	# return True if handled, False to fall through
    
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
            if self.fp.ClaimChildren:
                return self.fp.Base 
        return None

    def getIcon(self):
        """
        Return the icon in XMP format which will appear in the tree view. This method is optional and if not defined a default icon is shown.
        """

        return str(Path(__file__).parent / 'Recompose.svg')


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

def _create(obj, name="Recompose"):
    myObj = App.ActiveDocument.addObject("Part::FeaturePython", name)
    Recompose(myObj)
    myObj.Base= obj 
    ViewProviderRecompose(myObj.ViewObject)
    obj.ViewObject.Visibility=False
    App.ActiveDocument.recompute()
    return myObj

def create(name="Recompose"):
    sel = FreeCADGui.Selection.getSelectionEx()[0]
    return _create(sel.Object, name=name)

# -------------------------- Gui command --------------------------------------------------
if "FCMacro" in __file__:
	create()
else:
	from PySide import QtCore
	from PySide import QtGui

	def translate(context, text, disambig):
		#Recompose is not translatable, sorry...
		return text

	def activeBody():
		if App.ActiveDocument is None: return None
		if not hasattr(FreeCADGui.ActiveDocument.ActiveView, 'getActiveObject'): #prevent errors in 0.16
			return None
		return FreeCADGui.ActiveDocument.ActiveView.getActiveObject("pdbody")

	def CreateRecompose(name):
		App.ActiveDocument.openTransaction("Create Recompose")
		FreeCADGui.addModule("Recompose")
		FreeCADGui.doCommand("f = Recompose.create(name = '"+name+"')")
		FreeCADGui.doCommand("f = None")
		App.ActiveDocument.commitTransaction()

	class _CommandRecompose:
		"Command to create Recompose feature"
		def GetResources(self):
			return {'Pixmap'  : str(Path(__file__).parent / 'Recompose.svg'),
				'MenuText': QtCore.QT_TRANSLATE_NOOP("4axis_Recompose","Recompose"),
				'Accel': "",
				'ToolTip': QtCore.QT_TRANSLATE_NOOP("4axis_Recompose","Extrude individual shapes in a compound shape")}
        
		def Activated(self):
			CreateRecompose(name = "Recompose")
            
		def IsActive(self):
			return True
			if App.ActiveDocument:
				return activeBody() is None
			else:
				return False
            
	if App.GuiUp:
		FreeCADGui.addCommand('4Axis_Recompose', _CommandRecompose())
		print("Added Command")

	exportedCommands = ['4Axis_Recompose']
	print("I am Recompose!")
# -------------------------- /Gui command --------------------------------------------------
