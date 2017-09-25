import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

from NodeGraphics import *

import Events
import Style


class NodegraphPanel(QtGui.QFrame):
	def __init__(self, parent):
		super(NodegraphPanel, self).__init__(parent)
		self.setMinimumSize(250, 250)

		self.layout = QtGui.QVBoxLayout(self)
		self.layout.setContentsMargins(0, 0, 0, 0)
		self.layout.setSpacing(0)

		self.setLayout(self.layout)

		self.nodeGraphView = NodegraphView(self)
		self.layout.addWidget(self.nodeGraphView)


class NodegraphScene(QtGui.QGraphicsScene):
	def __init__(self):
		super(NodegraphScene, self).__init__()

	def mouseReleaseEvent(self, event):
		names = []
		for item in self.selectedItems():
			nodeName = item.getName()
			names.append(nodeName)

		Events.queueEvent('node_select', names=names)
		Events.processEvents()

		super(NodegraphScene, self).mouseReleaseEvent(event)


class NodegraphView(QtGui.QGraphicsView):
	'''
	QGraphicsView for displaying the nodes

	:param parent: QWidget/QFrame
	'''

	def __init__(self, parent):
		super(NodegraphView, self).__init__(parent)
		self.setObjectName('Node Graph View')
		self.scene = None
		self.initUi()

		self.__registerDirtyCallbacks()
		self.setViewportUpdateMode(QtGui.QGraphicsView.SmartViewportUpdate)

	def initUi(self):
		if self.scene is None:
			self.scene = NodegraphScene()
			self.scene.setObjectName('Node Graph')
			self.scene.setSceneRect(0, 0, 32000, 32000)
			self.setScene(self.scene)
		else:
			self.scene.clear()

		self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
		self.setViewportUpdateMode(QtGui.QGraphicsView.SmartViewportUpdate)
		self.drag = False

		self.zoomFactor = 1.0
		self.scaleFactor = 1.0
		self.nodeMap = {}

	def __registerDirtyCallbacks(self):
		Events.registerHandler(self.__addNode, 'node_create')
		Events.registerHandler(self.__addInputPort, 'node_addInputPort')
		Events.registerHandler(self.__addOutputPort, 'node_addOutputPort')
		Events.registerHandler(self.__portConnect, 'port_connect')
		Events.registerHandler(self.__clearNodes, 'node_clear')

	def __clearNodes(self):
		self.initUi()

	def getCentre(self):
		return self.scene.width() / 2, self.scene.height() / 2

	def __addNode(self, node):
		cx, cy = self.getCentre()
		nodeItem = NodeItem(name=node.getName(), type=node.getType())
		nodeItem.setPos(cx - nodeItem.width / 2, cy - nodeItem.height / 2)

		self.scene.addItem(nodeItem)
		self.nodeMap[node.getName()] = nodeItem
		nodeBaseType = node.getBaseType()

		nodeColours = Style.nodeColours['node']
		if nodeBaseType in nodeColours:
			nodeItem.setColour(nodeColours[nodeBaseType])
		else:
			nodeItem.setColour(nodeColours['default'])

		nodeFontColours = Style.nodeColours['node_font']
		if nodeBaseType in nodeFontColours:
			nodeItem.setFontColour(nodeFontColours[nodeBaseType])
		else:
			nodeItem.setFontColour(nodeFontColours['default'])

	def __addInputPort(self, node, portName):
		nodeName = node.getName()
		if nodeName not in self.nodeMap: return
		self.nodeMap[nodeName].addInputPort(portName)

	def __addOutputPort(self, node, portName):
		nodeName = node.getName()
		if nodeName not in self.nodeMap: return
		self.nodeMap[nodeName].addOutputPort(portName)

	def __portConnect(self, nodeFrom, nodeTo, portIn, portOut):
		if nodeFrom not in self.nodeMap or nodeTo not in self.nodeMap:
			# TODO: Log
			return

		nodeItemFrom = self.nodeMap[nodeFrom]
		nodeItemTo = self.nodeMap[nodeTo]
		if portOut not in nodeItemFrom.outputs:
			# TODO: Log
			return

		if portIn not in nodeItemTo.inputs:
			# TODO: Log
			return

		nodeItemFrom.outputs[portOut].connect(nodeItemTo.inputs[portIn])

		# Connect ports with a noodle
		portItemOut = nodeItemFrom.outputs[portOut]
		portItemIn = nodeItemTo.inputs[portIn]

		pointA, pointB = portItemOut.getCentre(), portItemIn.getCentre()
		newLine = Noodle(pointA, pointB)
		newLine.source = portItemOut
		newLine.target = portItemIn
		newLine.updatePath()
		portItemOut.outLines.append(newLine)
		portItemIn.inLines.append(newLine)
		self.scene.addItem(newLine)

	def wheelEvent(self, event):
		inFactor = 1.1
		outFactor = 1 / inFactor
		oldPos = self.mapToScene(event.pos())
		if event.delta() > 0:
			if self.scaleFactor * inFactor > 12.: return
			self.zoomFactor = inFactor
			self.scaleFactor *= inFactor
		else:
			if self.scaleFactor * outFactor < 0.05: return
			self.zoomFactor = outFactor
			self.scaleFactor *= outFactor

		# cameraZoomScale = pow(1.1, self.zoomFactor)
		# self.scale(cameraZoomScale, cameraZoomScale)
		# newPos = self.mapToScene(event.pos())
		# compute the 2d correction to make the zoom operate at (x,y)
		# delta = newPos - oldPos
		# dx, dy = (x - 0.5 * self.width), (y - 0.5 * self.height)
		# cx = ( - delta.x) * cameraZoomScale + dx
		# self.camera.cameraOy = (self.camera.cameraOy - dy) * cameraZoomScale + dy

		self.scale(self.zoomFactor, self.zoomFactor)
		newPos = self.mapToScene(event.pos())
		delta = newPos - oldPos
		# dx, dy = (self.x() - 0.5 * self.width()), (self.y() - 0.5 * self.height())
		# print delta, dx, dy
		self.translate(delta.x(), delta.y())
		# self.centerOn(newPos)

	def __resetScale(self):
		if self.scaleFactor > 0:
			self.zoomFactor = 1 / self.scaleFactor
		else:
			self.zoomFactor = 1 + self.scaleFactor

		self.scale(self.zoomFactor, self.zoomFactor)
		self.scaleFactor = 1.0

	def __getUnitedRect(self, selectedItems, padding=60):
		if not selectedItems:
			# Check if
			selectedItems = self.nodeMap.values()

		unitedRegion = QtGui.QPolygonF()
		for item in selectedItems:
			unitedRegion = unitedRegion.united(item.getRect())

		unitedRect = unitedRegion.boundingRect()

		if padding > 0:
			unitedRect.setX(unitedRect.x() - padding)
			unitedRect.setWidth(unitedRect.width() + padding)
			unitedRect.setY(unitedRect.y() - padding)
			unitedRect.setHeight(unitedRect.height() + padding)

		centre = QtCore.QPoint(unitedRect.x() + unitedRect.width() / 2, unitedRect.y() + unitedRect.height() / 2)
		return unitedRect

	def focus(self):
		unitedRect = self.__getUnitedRect(self.scene.selectedItems())
		self.fitInView(unitedRect, QtCore.Qt.KeepAspectRatio)

	def keyPressEvent(self, event):
		if event.key() == QtCore.Qt.Key_F:
			self.focus()

	def mousePressEvent(self, event):
		if event.button() == QtCore.Qt.MiddleButton and event.modifiers() == QtCore.Qt.AltModifier:
			self.setDragMode(QtGui.QGraphicsView.NoDrag)
			self.drag = True
			self.prevPos = event.pos()
			self.setCursor(QtCore.Qt.SizeAllCursor)
		elif event.button() == QtCore.Qt.LeftButton:
			self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)

		super(NodegraphView, self).mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self.drag:
			delta = (self.mapToScene(event.pos()) - self.mapToScene(self.prevPos)) * -1.0
			center = QtCore.QPoint(self.viewport().width() / 2 + delta.x(), self.viewport().height() / 2 + delta.y())
			newCenter = self.mapToScene(center)
			self.centerOn(newCenter)
			self.prevPos = event.pos()
			return

		super(NodegraphView, self).mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		if self.drag:
			self.drag = False
			self.setCursor(QtCore.Qt.ArrowCursor)

		super(NodegraphView, self).mouseReleaseEvent(event)

	def _updateBounds(self, bounds, point):
		if point[0] < bounds[0]:
			bounds[0] = point[0]
		if point[0] > bounds[2]:
			bounds[2] = point[0]
		if point[1] < bounds[1]:
			bounds[1] = point[1]
		if point[1] > bounds[3]:
			bounds[3] = point[1]

	def _getTransformFunction(self, startBounds, endBounds):
		'''
		Get a function to transform (x,y) tuples from startBounds to endBounds
		'''
		sx, sy = 1.4, 1.8
		tx = ((endBounds[0] + endBounds[2]) - (startBounds[0] + startBounds[2])) / 2.0 + 16000
		ty = ((endBounds[1] + endBounds[3]) - (startBounds[1] + startBounds[3])) / 2.0 + 16000

		return lambda (x, y): (
			(x - startBounds[0]) * sx + startBounds[0] + tx,
			(y - startBounds[1]) * sy + startBounds[1] + ty
		)

	def positionNodes(self, nodes=None):
		try:
			import pygraphviz
		except:
			raise RuntimeError('You need pygraphviz to use this feature')

		if nodes is None:
			selectedItems = self.scene.selectedItems()
			if selectedItems:
				nodes = selectedItems
			else:
				nodes = self.nodeMap.values()

		# origBounds = self.__getUnitedRect(nodes)
		# print origBounds

		inf = float('inf')
		nodeGraphBounds = [inf, inf, -inf, -inf]
		graphVizBounds = [inf, inf, -inf, -inf]
		fontName = 'monospace'

		g = pygraphviz.AGraph(strict=True, directed=True, rankdir='LR', fixedsize=True)

		for nodeItem in nodes:
			# pos = Nodegraph.GetNodePosition(n)
			pos = nodeItem.getPosition()
			self._updateBounds(nodeGraphBounds, pos)

			nodeName = nodeItem.getName()
			# g.node_attr.update(height=nodeItem.rect.height() / 100)
			g.add_node(nodeName)
			# n = g.get_node(nodeName)
			# n.attr['width'] = nodeItem.rect.width() / 100.
			# print n.attr.keys()
			# n.attr['height'] = nodeItem.rect.height() / 100.
			# print g.node_attr.keys()

			for inPort in nodeItem.getInputPorts():
				for port in inPort.getConnectedPorts():
					g.add_edge(port.getNode().getName(), nodeName)

			for outPort in nodeItem.getOutputPorts():
				for port in outPort.getConnectedPorts():
					g.add_edge(nodeName, port.getNode().getName())

		g.layout(prog='dot', args='-Nfontname="%s"' % fontName)

		positions = dict()
		for node in nodes:
			name = node.getName()
			graphNode = g.get_node(name)
			posAttr = graphNode.attr['pos']
			position = map(float, posAttr.split(','))
			positions[name] = position
			self._updateBounds(graphVizBounds, position)

		# Transform back to where we were
		rescale = self._getTransformFunction(graphVizBounds, nodeGraphBounds)

		for node in nodes:
			name = node.getName()
			# NodegraphAPI.SetNodePosition(n, rescale(positions[name]))
			node.setPosition(rescale(positions[name]))
			# node.setPosition(positions[name])
			node.updatePortsAndNoodles()

		self.focus()
