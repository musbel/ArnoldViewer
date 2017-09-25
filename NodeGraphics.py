import PySide.QtGui as QtGui
import PySide.QtCore as QtCore
import numpy as np

import Events

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Noodle(QtGui.QGraphicsPathItem):
	def __init__(self, pointA, pointB):
		super(Noodle, self).__init__()
		self._pointA = pointA
		self._pointB = pointB
		self._source = None
		self._target = None
		self.setZValue(-1)
		self.setBrush(QtCore.Qt.NoBrush)
		self.pen = QtGui.QPen()
		self.pen.setStyle(QtCore.Qt.SolidLine)
		self.pen.setWidth(2)
		self.pen.setColor(QtGui.QColor(150, 150, 150, 255))
		self.setPen(self.pen)

	def mousePressEvent(self, event):
		self.pointB = event.pos()

	def mouseMoveEvent(self, event):
		self.pointB = event.pos()

	def updatePath(self):
		path = QtGui.QPainterPath()
		path.moveTo(self.pointA)
		dx = self.pointB.x() - self.pointA.x()
		dy = self.pointB.y() - self.pointA.y()
		ctrl1 = QtCore.QPointF(self.pointA.x() + dx * 0.25, self.pointA.y() + dy * 0.1)
		ctrl2 = QtCore.QPointF(self.pointA.x() + dx * 0.75, self.pointA.y() + dy * 0.9)
		path.cubicTo(ctrl1, ctrl2, self.pointB)
		self.setPath(path)

	def paint(self, painter, option, widget):
		painter.setPen(self.pen)
		painter.drawPath(self.path())

	@property
	def pointA(self):
		return self._pointA

	@pointA.setter
	def pointA(self, point):
		self._pointA = point
		self.updatePath()

	@property
	def pointB(self):
		return self._pointB

	@pointB.setter
	def pointB(self, point):
		self._pointB = point
		self.updatePath()

	@property
	def source(self):
		return self._source

	@source.setter
	def source(self, widget):
		self._source = widget

	@property
	def target(self):
		return self._target

	@target.setter
	def target(self, widget):
		self._target = widget


class NodePort(QtGui.QGraphicsItem):
	def __init__(self, parent, rect, socketName, socketType):
		super(NodePort, self).__init__(parent)
		self.rect = rect
		self.name = socketName
		self.type = socketType
		self.parent = parent

		self.labelFont = QtGui.QFont('monospace')
		self.labelFont.setPixelSize(6)
		self.highlightLabelFont = QtGui.QFont('monospace')
		self.highlightLabelFont.setPixelSize(10)
		self.labelItem = QtGui.QGraphicsTextItem(self.name, self, self.scene())
		self.labelItem.setDefaultTextColor(QtGui.QColor(200, 200, 200, 255))
		self.labelItem.setFont(self.labelFont)

		# Brush
		self.brush = QtGui.QBrush()
		self.brush.setStyle(QtCore.Qt.SolidPattern)
		self.brush.setColor(QtGui.QColor(70, 70, 70, 255))

		# Pen
		self.pen = QtGui.QPen()
		self.pen.setStyle(QtCore.Qt.SolidLine)
		self.pen.setWidth(1)
		self.pen.setColor(QtGui.QColor(50, 50, 50, 255))

		# Pen - Highlighted
		self.highlightPen = QtGui.QPen()
		self.highlightPen.setStyle(QtCore.Qt.SolidLine)
		self.highlightPen.setWidth(1)
		self.highlightPen.setColor(QtGui.QColor(255, 255, 0, 255))

		# Pen - Text
		self.textPen = QtGui.QPen()
		self.textPen.setColor(QtGui.QColor(230, 230, 230, 255))

		# Lines
		self.outLines = []
		self.inLines = []

		self.connectedPorts = []

		self.highlight = False
		self.setAcceptHoverEvents(True)
		# self.setCacheMode(QtGui.QGraphicsItem.DeviceCoordinateCache)

	def getName(self):
		return self.name

	def connect(self, port):
		self.connectedPorts.append(port)

	def getNode(self):
		return self.parent

	def getConnectedPorts(self):
		return self.connectedPorts

	def shape(self):
		path = QtGui.QPainterPath()
		path.addEllipse(self.boundingRect())
		return path

	def boundingRect(self):
		return QtCore.QRectF(self.rect)

	def updateY(self, y):
		self.rect.moveTop(y)
		self.update()

	def getCentre(self):
		rect = self.boundingRect()
		centre = QtCore.QPointF(rect.x() + rect.width() / 2, rect.y() + rect.height() / 2)
		centre = self.mapToScene(centre)
		return centre

	def paint(self, painter, option, widget):
		if self.highlight:
			painter.setPen(self.highlightPen)
			self.labelItem.setFont(self.highlightLabelFont)
		else:
			painter.setPen(self.pen)
			self.labelItem.setFont(self.labelFont)

		painter.setBrush(self.brush)
		painter.drawEllipse(self.rect)

		bounds = self.boundingRect()
		textBounds = self.labelItem.boundingRect()
		d = bounds.height() / 2 - textBounds.height() / 2
		if self.type == 'in':
			self.labelItem.setPos(bounds.x() - textBounds.width(), bounds.y() + d)
		else:
			self.labelItem.setPos(bounds.x() + bounds.width(), bounds.y() + d)

	def hoverEnterEvent(self, event):
		if not self.highlight:
			self.highlight = True
			self.update()

	def hoverLeaveEvent(self, event):
		if self.highlight:
			self.highlight = False
			self.update()

	def mousePressEvent(self, event):
		if self.type == 'out':
			pointA = self.getCentre()
			pointB = self.mapToScene(event.pos())

			self.newLine = Noodle(pointA, pointB)
			self.outLines.append(self.newLine)
			self.scene().addItem(self.newLine)

		elif self.type == 'in':
			pointA = self.mapToScene(event.pos())
			pointB = self.getCentre()

			self.newLine = Noodle(pointA, pointB)
			self.inLines.append(self.newLine)
			self.scene().addItem(self.newLine)

		else:
			super(NodePort, self).mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if self.type == 'out':
			pointB = self.mapToScene(event.pos())
			self.newLine.pointB = pointB

		elif self.type == 'in':
			pointA = self.mapToScene(event.pos())
			self.newLine.pointA = pointA

		else:
			super(NodePort, self).mouseMoveEvent(event)

	def mouseReleaseEvent(self, event):
		item = self.scene().itemAt(event.scenePos().toPoint())
		if item is None: return

		if self.type == 'out' and item.type == 'in':
			Events.queueEvent('port_connect', nodeFrom=self.parent.getName(), nodeTo=item.parentItem().getName(),
							  portIn=item.name, portOut=self.name)
		elif self.type == 'in' and item.type == 'out':
			Events.queueEvent('port_connect', nodeFrom=item.parentItem().getName(), nodeTo=self.getParent().getName(),
							  portIn=self.getName(), portOut=item.getName())
		else:
			super(NodePort, self).mouseReleaseEvent(event)

		self.scene().removeItem(self.newLine)
		Events.processEvents()


class NodeItem(QtGui.QGraphicsItem):
	def __init__(self, name, type):
		super(NodeItem, self).__init__()

		self.inputs = {}
		self.outputs = {}

		self.initUi()

		self.type = type
		self.setName(name)

	def addInputPort(self, portName):
		y = self.height / 2 - self.portHeight / 2
		rect = QtCore.QRect(self.x - self.portWidth / 2, y, self.portWidth, self.portHeight)

		self.inputs[portName] = NodePort(self, rect, portName, 'in')
		self.__updatePorts()

	def addOutputPort(self, portName):
		y = self.height / 2 - self.portHeight / 2
		rect = QtCore.QRect(self.width - self.portWidth / 2, y, self.portWidth, self.portHeight)

		self.outputs[portName] = NodePort(self, rect, portName, 'out')
		self.__updatePorts()

	def getInputPorts(self):
		return self.inputs.values()

	def getOutputPorts(self):
		return self.outputs.values()

	def __updatePorts(self):
		# Adjust the node height to accommodate the number of ports
		self.__updateSize()

		# Input ports
		socketPositions = np.linspace(0, self.height, len(self.inputs) + 2, endpoint=True)[1:-1]
		for (portName, port), posY in zip(self.inputs.iteritems(), socketPositions):
			port.updateY(posY - self.portHeight / 2)

		# Output ports
		socketPositions = np.linspace(0, self.height, len(self.outputs) + 2, endpoint=True)[1:-1]
		for (portName, port), posY in zip(self.outputs.iteritems(), socketPositions):
			port.updateY(posY - self.portHeight / 2)

	def initUi(self):
		self.x, self.y = 0, 0
		self.width, self.height = 100, 60

		self.rect = QtCore.QRect(self.x, self.y, self.width, self.height)
		self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
		self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)

		self.portWidth, self.portHeight = 10, 10

		# Brush
		self.brush = QtGui.QBrush()
		self.brush.setStyle(QtCore.Qt.SolidPattern)
		self.brush.setColor(QtGui.QColor(120, 120, 120, 255))

		# Pen
		self.pen = QtGui.QPen()
		self.pen.setStyle(QtCore.Qt.SolidLine)
		self.pen.setWidth(1)
		self.pen.setColor(QtGui.QColor(60, 60, 60, 255))

		self.selPen = QtGui.QPen()
		self.selPen.setStyle(QtCore.Qt.SolidLine)
		self.selPen.setWidth(1)
		self.selPen.setColor(QtGui.QColor(255, 255, 0, 255))

		# Pen - Text
		self.textPen = QtGui.QPen()
		self.textPen.setColor(QtGui.QColor(230, 230, 230, 255))

	def setName(self, name):
		self.name = name if name else 'Anonyomus'
		self.__updateSize()

	def getName(self):
		return self.name

	def setColour(self, colour):
		self.brush.setColor(QtGui.QColor(colour[0], colour[1], colour[2], colour[3]))

	def setFontColour(self, colour):
		self.textPen.setColor(QtGui.QColor(colour[0], colour[1], colour[2], colour[3]))

	def getCentre(self):
		rect = self.boundingRect()
		centre = QtCore.QPointF(rect.x() + rect.width() / 2, rect.y() + rect.height() / 2)
		centre = self.mapToScene(centre)
		return centre

	def setPosition(self, position):
		self.setX(position[0])
		self.setY(position[1])

	def getPosition(self):
		return (self.x, self.y)

	def getRect(self):
		return self.mapToScene(self.rect)

	def __updateSize(self):
		# Update width based on name
		wordLength = max(len(self.name), len(self.type))
		self.width = max(100, wordLength * 8 + 10)

		# Update height based on number of ports (10 each plus padding)
		maxNumPorts = max(len(self.inputs), len(self.outputs))
		self.height = max(60, maxNumPorts * 20 + 10)

		self.rect.setWidth(self.width)
		self.rect.setHeight(self.height)

	def shape(self):
		path = QtGui.QPainterPath()
		path.addRect(self.boundingRect())
		return path

	def boundingRect(self):
		return QtCore.QRectF(self.rect)

	def paint(self, painter, option, widget):
		painter.setBrush(self.brush)
		if self.isSelected():
			painter.setPen(self.selPen)
		else:
			painter.setPen(self.pen)

		painter.setRenderHints(
			QtGui.QPainter.Antialiasing |
			QtGui.QPainter.SmoothPixmapTransform |
			QtGui.QPainter.HighQualityAntialiasing)

		painter.drawRoundedRect(self.rect, 6.0, 6.0)

		font = QtGui.QFont('monospace')
		painter.setFont(font)
		textOption = QtGui.QTextOption()
		textOption.setAlignment(QtCore.Qt.AlignCenter)
		painter.setPen(self.textPen)
		# nodeLabel = '{}\n({})'.format(self.name, self.type)
		nodeLabel = self.name
		painter.drawText(self.rect, nodeLabel, textOption)

	def mouseMoveEvent(self, event):
		super(NodeItem, self).mouseMoveEvent(event)
		self.updatePortsAndNoodles()

	def updatePortsAndNoodles(self):
		for outputName, output in self.outputs.iteritems():
			for line in output.outLines:
				if line.source is not None and line.target is not None:
					line.pointA = line.source.getCentre()
					line.pointB = line.target.getCentre()

		for inputName, input in self.inputs.iteritems():
			for line in input.inLines:
				if line.source is not None and line.target is not None:
					line.pointA = line.source.getCentre()
					line.pointB = line.target.getCentre()

	def contextMenuEvent(self, event):
		pass
		# menu = QtGui.QMenu()
		# debugConnections = menu.addAction('debug connections')
		# selectedAction = menu.exec_(event.screenPos())

		# if selectedAction == debugConnections:
		# 	pass

