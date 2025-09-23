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

def fixPlacement(s,p):
	s.Placement=p
	return s

def EdgeToBiArcs(Edge, tolerance=0.01):
	if type(Edge.Curve) in [ Part.Line, Part.Circle ]:
		l=  Edge.Curve.toNurbs(Edge.FirstParameter,Edge.LastParameter)
		l = l.toBiArcs(tolerance)
	else:
		l = Edge.Curve.toBiArcs(tolerance)
	return l

def EdgeToBSpline(e):
	try:
		c=e.toNurbs().Edge1.Curve
	except:
		print("Nurbs Fail")
		c=e.Curve.toBSpline()
	c.segment(e.FirstParameter,e.LastParameter)
	return c

def joinShape(shp):
	bs = [ EdgeToBSpline(e) for e in shp.Edges ]

	c=bs[0]

	for b in bs[1:]:
		if not c.join(b):
			print("JoinFail")
#			forcejoin(c,b)
	return c.toShape()

def getRad(c):
	if type(c) in [Part.Circle, Part.ArcOfCircle]:
		return c.Radius
	else:
		return 1000000

def splitGeo(c):
	a=c.copy()
	b=c.copy()

	a.setParameterRange(a.FirstParameter, (a.FirstParameter+a.LastParameter)/2)
	b.setParameterRange(a.LastParameter, b.LastParameter)
	return a,b

def splitGeoByLen(c,l):
	if(l<=0):
		raise Exception("BUG! can't splitGeoByLen by <=0 length!")

	a=c.copy()
	b=c.copy()

	r=a.LastParameter-a.FirstParameter
	l=l/a.length()
	r*=l
	r+=a.FirstParameter

#	print("splitGeoByLen: ", a.FirstParameter, r, b.LastParameter)
	if type(c) in [Part.LineSegment,Part.BSplineCurve ]:
		a = a.toNurbs(a.FirstParameter,r)
		b = b.toNurbs(r, b.LastParameter)
#		print("type b=",type(b))
	else:
		a.setParameterRange(a.FirstParameter, r)
		b.setParameterRange(r, b.LastParameter)
	return a,b

def SegmentByLength(l, lenlist):	# lenlist must be sorted in reverse order
	i=j=0
	curlen=0
	cmplen=0

	while j<len(l):
		if not cmplen:
			try:
				cmplen=lenlist.pop()
			except:
				yield l[i:]
				return

		if curlen+l[j].length()>cmplen:
			a,b = splitGeoByLen(l[j], cmplen-curlen)
			l[j]=a
			yield l[i:j+1]
			curlen+= a.length()	# b's length will be added below
			i=j
			l[j]=b
			cmplen=0	# cause pop of new cmplen
			continue	# re-asess the second part of the curve in case it's long enough to go past the next length
		elif cmplen+l[j].length()==cmplen:
			yield l[i:j+1]
			i=j+1

		curlen+= l[j].length()
		j+=1

	yield l[-1]
			
def SegmentByRadius( l, radii):
	i=j=0
	curlen=0
	while j<len(l):
		while j<len(l) and not getRad(l[j]) in radii:
			j+=1
		if(True and j<len(l)):
			a,b = splitGeo(l[j])
			l[j]=a
			yield l[i:j+1]
			l[j]=b
		else:
			yield l[i:j]
		i=j
		j+=1

def makeCumulative(l):
	acc=0

	for i in l:
		acc+=i
		yield acc
		
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

#def DistanceToParam(edge, distance):
#	rnge = edge.LastParameter-edge.FirstParameter
#
#	off = rnge*distance/edge.Length
#	return edge.FirstParameter+off
	
class Recompose:
	def __init__(self, obj):
		obj.Proxy = self
		obj.addProperty("App::PropertyLinkList", "Base", "Dimensions")
		obj.addProperty("App::PropertyFloatConstraint", "Tolerance", "Dimensions").Tolerance=(0.01, 0.0, 1000.0, 0.01)
		obj.addProperty("App::PropertyEnumeration", "Mode", "Split").Mode=['Nothing', 'Just Join', 'Split by Distance', 'Split by Radii']
		obj.Mode=1
		obj.addProperty("App::PropertyFloatList", "SplitDistances", "Split").SplitDistances=[ ]
		obj.addProperty("App::PropertyFloatConstraint", "SplitDistance", "Split").SplitDistance= (0.0, 0.0, 100000000000, 0.1)	# value, min, max, step
		obj.addProperty("App::PropertyBool", "AddDistance", "Split").AddDistance=False
		obj.addProperty("App::PropertyInteger", "NumRadii", "Split").NumRadii=1
		obj.addProperty("App::PropertyFloatList", "RadiusSplits", "Split").RadiusSplits=[]
		obj.addProperty("App::PropertyBool", "ClaimChildren", "Dimensions").ClaimChildren=True

	def onDocumentRestored(self, obj):
		pass

	def execute(self, obj):
		s = joinEdges( obj.Base[0].Shape.Edges)
		if not s:
			raise Exception("{obj.Name}:Can't join")

		if obj.SplitDistance:
			p = e.getParameterByLength(obj.SplitDistance)
			w = e.split(p)
			obj.Shape=w
			# dumb test
			l= [ e.reversed() for e in w.Edges]
			obj.Shape = joinEdges(l)
		else:
			obj.Shape=s
		return

		c = [ EdgeToBiArcs(e,obj.Tolerance) for e in obj.Base[0].Shape.Edges ]
		c = [ i for sub in c for i in sub ]	# combine the list of lists into a single list of elements

		# a dirty test, ignore all properties nd just do the length split!

		if 'Distance' in obj.Mode:
			dlist=obj.SplitDistances.copy()
			if obj.SplitDistance:
				dlist.append( obj.SplitDistance)
			dlist=list(set(dlist))
			dlist.sort()
			dlist.reverse()
#			print("dlist=",dlist)
			j = [ joinShape(Part.makeCompound(e)) for e in SegmentByLength(c, dlist ) ]
#			print(j)
			c=Part.makeCompound(j)
		elif 'Radii' in obj.Mode and obj.NumRadii>0:
			r = [ getRad(i) for i in c]
			r = list(dict.fromkeys(r))	# de-dup list
			r.sort()

			j = [ joinShape(Part.makeCompound(e)) for e in SegmentByRadius(c, r[:obj.NumRadii] ) ]
			c=Part.makeCompound(j)
			l=[ i.Length for i in c.Edges ]
			obj.RadiusSplits = [ i for i in makeCumulative(l[:-1])] if len(l)>1 else []

		elif 'Join' in obj.Mode:
			c=Part.makeCompound(c)
			c = joinShape(c)
		else:
			c=Part.makeCompound(c)

		obj.Shape=c
		return

	def onChanged(self, obj, name):
		if name == 'AddDistance':
			if obj.AddDistance:
				l=obj.SplitDistances
				l.append(obj.SplitDistance)
				obj.SplitDistances = l
				obj.AddDistance=False
#				print("Added")
		if name in ['NumRadii', 'Tolerance', 'SplitDistance']:
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
