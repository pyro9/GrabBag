# find the peaks and troughs of a b-spline

#sample the bspline, at each point, compute the "down" vector. Either the reversed normal of the base points of the bspline, or 
#for periodic bSplines,a vector from the sample to tyhe CenterOfGravity of the shape.
#Take the Arc Cosine of the dot product of the vectors. It will = 90 degrees (1.5707963268 radians) exactly at a peak or a trough (local max or min).

from math import acos, pi

import Part



def Spaceship(test, standard, tolerance=0.0):
	if abs(test-standard) < tolerance:
		return 0
	return -1 if test<standard else 1               

def float_range(start, stop, step):
	current = start
	while current < stop:
		yield current
		current += step

class ComputeMinMax:
	def __init__(self, edge, downmode='Auto'):
		self.debug=False
		self.edge = edge
		self.deg90 = pi/2
		self._params=None
		self.down=None
		self.Mode = downmode

		if ('Auto' in self.Mode and edge.isClosed()) or 'CG' in self.Mode:
			self.cg = edge.CenterOfGravity
			self.down=None
		else:
			self.down = self.computeDown()
			self.cg=None

	def computeDown(self, start=None, end=None):	# it might accidentally compute UP, but that works the same for this purpose
		if start==None:
			start=self.edge.FirstParameter
		if end==None:
			end=self.edge.LastParameter

		mid = (start+end)/2

		v=self.edge.valueAt(start) - self.edge.valueAt(end)
		v2 = self.edge.valueAt(start)-self.edge.valueAt(mid)

		v3 = v.cross(v2)	# v3 is the hinge between the line to the end of the curve and to an arbitrary point on the curve

		vres = v3.cross(v)	# vres is the hinge between the baseline v and the hinge computed above.
							# It also happens to point down
		vres.normalize()

		# testing
		if self.debug:
			vt = Part.Vertex(self.edge.valueAt(mid))
			l=vt.extrude(50*vres)
			Part.show(l).Label='Down'
			v4=self.edge.tangentAt(mid)
			l2=vt.extrude(10*v4)
			Part.show(l2).Label='Tangent'
		return vres
	
	def getDown(self, U=None):
		if self.down:
			return self.down

		point = self.edge.valueAt(U)
		bv=point-self.cg
		bv.normalize()
		return bv

	def computeSlopeTheta(self, U):
		tangent = self.edge.tangentAt(U)
		bv = self.getDown(U)

		try:
			theta = acos(bv*tangent)
		except:
			print( "Math error:",bv, tangent)
		return theta

	def findMinMax(self, start=None, end=None, tol=0.0001, level=5):
		edge=self.edge

		if start==None:
			start=self.edge.FirstParameter
		if end==None:
			end=self.edge.LastParameter

		uLen = end-start
		lastP=start
		lastT = self.computeSlopeTheta(start)
		res = Spaceship(lastT, self.deg90,tol)
	
#	print(f"MinMax enter: level: {level}, lastP:{lastP}, lastT: {lastT}, res: {res}")
		
		for p in float_range(start, end, uLen/1000):
			theta = self.computeSlopeTheta(p)

			if not res:
				res = Spaceship(theta, self.deg90,tol)
				lastT = theta
				lastP = p
#				print(f"Skipping: p={p}, newres={res}")
				continue

			newres = Spaceship(theta, self.deg90, tol)
			if not newres:
					return p
				
#		print(f"MinMax progress: p:{p}, theta:{theta}, newres={newres}")
			if newres != res:
				level-=1
				if not level:
					return (lastP+p)/2
#					raise Exception("Recursion too deep")
				return self.findMinMax(lastP, p, tol=tol, level=level)
			else:
				lastP=p
				lastT=theta
		if self.debug:
			print(f"MinMax returns: level: {level}, Start:{start}, End: {end}, lastP: {lastP}")
		return None

	def findAllMinMax(self, start=None, end=None, tol=0.0001, level=5):
		if start==None:
			start=self.edge.FirstParameter
		if end==None:
			end = self.edge.LastParameter

		all = []
		p = start
		pStep = (self.edge.LastParameter - self.edge.FirstParameter)/1000
	
		theta = self.computeSlopeTheta(p)
		if not Spaceship(theta, self.deg90, tol):
			all.append(p)
		
		while p+pStep < self.edge.LastParameter: #remember, floating point might approximate
			p = self.findMinMax(p, self.edge.LastParameter, tol=tol, level=level)
			if p == None:
				break

			all.append(p)

		self._params = all
		return all

	@property
	def params(self):
		if self._params:
			return self._params
		else:
			return self.findAllMinMax()

	@property
	def distances(self):
		pFact = self.edge.Length/(self.edge.LastParameter - self.edge.FirstParameter)
		return [ U*pFact for U in self.params ]

def Degrees(rad):
	return rad*180/pi
		
def test():
	import FreeCADGui

	sel = FreeCADGui.Selection.getSelectionEx()[0]
	e = sel.Object.Shape.__getattribute__(sel.SubElementNames[0])

	CMM = ComputeMinMax(e)
	CMM.debug=True
	CMM.computeDown()

	params = CMM.params

	for p in params:
		if p!=None:
			print( (p, Degrees(CMM.computeSlopeTheta(p)) ))
		else:
			print(None)

	pFactor = e.Length/( CMM.edge.LastParameter - CMM.edge.FirstParameter)
	d = CMM.distances


	vertices = [ Part.Vertex(CMM.edge.valueAt(v)) for v in params ]
	c=Part.makeCompound(vertices)
	obj = Part.show(c)
	obj.Label='MinMax'
	obj.addProperty("App::PropertyFloatList", "Distances", "Result")
	obj.Distances = d
