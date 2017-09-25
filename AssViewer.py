import sys, os
import functools
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

from arnold import *

import Nodegraph
import Events
import Style

from NodegraphPanel import NodegraphPanel
from ParameterPanel import ParameterPanel


class NodeWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		super(NodeWindow, self).__init__(parent)
		self.setWindowTitle('ASS Node Viewer')
		self.openFilename = None
		self.docks = {}

		self.initUi()

	def initUi(self):
		self.setMinimumSize(500, 250)
		self.resize(800, 500)

		allowedAreas = (QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)

		# Node Graph Panel
		self.nodeGraphPanel = NodegraphPanel(self)
		self.addDock('Node Graph', self.nodeGraphPanel, allowedAreas, QtCore.Qt.LeftDockWidgetArea)

		# Attribute Panel
		self.parameterPanel = ParameterPanel(self)
		self.addDock('Parameters', self.parameterPanel, allowedAreas, QtCore.Qt.RightDockWidgetArea)

		self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtGui.QTabWidget.North)
		self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtGui.QTabWidget.East)
		self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtGui.QTabWidget.West)
		self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtGui.QTabWidget.North)

		self.setStyleSheet(Style.css)
		self.initialiseMenu()

	def addWidget(self, widget, dockName, area=QtCore.Qt.LeftDockWidgetArea):
		self.docks[dockName] = widget
		allowedAreas = (QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
		self.addDock(dockName, self.docks[dockName], allowedAreas, area)

	def addDock(self, title, widget, allowedAreas, area):
		dock = QtGui.QDockWidget(title, self)
		dock.setWidget(widget)
		dock.setAllowedAreas(allowedAreas)
		self.addDockWidget(area, dock)
		return dock

	def initialiseMenu(self):
		self.menus = {}
		self.menuBar = QtGui.QMenuBar()
		self.setMenuBar(self.menuBar)

		fileMenu = self.getOrCreateMenu('File')
		self.addMenuItem({
			'menu': 'File', 'item': 'New',
			'cmd': self.new, 'args': []
		})
		self.addMenuItem({
			'menu': 'File', 'item': 'Open...',
			'cmd': self.openAssFile, 'args': [None, False]
		})
		self.addMenuItem({
			'menu': 'File', 'item': 'Open (preview)...',
			'tip': 'This visualises the nodes using minimal number of ports',
			'cmd': self.openAssFile, 'args': [None, True]
		})
		self.addMenuItem({
			'menu': 'File', 'item': 'Save...',
			'tip': '',
			'cmd': self.saveAssFile, 'args': [None]
		})

		viewMenu = self.getOrCreateMenu('View')

		self.getOrCreateMenu('Tools')
		self.addMenuItem({
			'menu': 'Tools', 'item': '&Render (kick)',
			'cmd': self.kick, 'args': []
		})
		self.addMenuItem({
			'menu': 'Tools', 'item': '&Position Nodes',
			'cmd': self.nodeGraphPanel.nodeGraphView.positionNodes, 'args': [] # TODO: Refactor using Events
		})

		self.getOrCreateMenu('Add Node')
		nodeGroups = {}
		nodes = Nodegraph.getRegisteredNodes()
		for nodeName, nodeInfo in nodes.iteritems():
			nodeGroups.setdefault(nodeInfo['baseType'], []).append(nodeName)

		for groupName, nodeNames in nodeGroups.iteritems():
			if not nodeNames: continue
			self.getOrCreateMenu(groupName, parent='Add Node')

			nodeNames.sort()
			for nodeName in nodeNames:
				self.addMenuItem({
					'menu': groupName, 'item': nodeName,
					'cmd': Nodegraph.createNode, 'args': [nodeName, None, False]
				})

	def getOrCreateMenu(self, menu, parent=None):
		if not self.menus.has_key(menu):
			if parent is None:
				self.menus[menu] = self.menuBar.addMenu(menu)
			else:
				if parent not in self.menus: return None
				self.menus[menu] = self.menus[parent].addMenu(menu)

		return self.menus[menu]

	def addMenuItem(self, menu_dict):
		menu = self.getOrCreateMenu(menu_dict['menu'])
		action = QtGui.QAction(menu_dict['item'], self)
		if 'shortcut' in menu_dict: action.setShortcut(menu_dict['shortcut'])
		if 'tip' in menu_dict: action.setStatusTip(menu_dict['tip'])
		cmd = eval(menu_dict['cmd']) if isinstance(menu_dict['cmd'], str) else menu_dict['cmd']
		if 'args' in menu_dict:
			cmd = functools.partial(cmd, *menu_dict['args'])

		action.triggered.connect(functools.partial(cmd))
		for old_action in menu.actions():
			if action.text() == old_action.text():
				menu.insertAction(old_action, action)
				menu.removeAction(old_action)
				return action
		menu.addAction(action)
		return action

	def kick(self):
		if self.openFilename:
			AiBegin()
			AiASSLoad(self.openFilename, AI_NODE_ALL)
			AiRender(AI_RENDER_MODE_CAMERA)
			AiEnd()

			# import subprocess
			# cmd = ['kick', self.openFilename]
			# subprocess.call(cmd, env=os.environ.copy())

	def new(self):
		Nodegraph.clearNodes()
		self.openFilename = None
		Events.processEvents()

	def saveAssFile(self, assFilename=None):
		if assFilename is None:
			fileName, desc = QtGui.QFileDialog.getSaveFileName(self, 'Save file', '%s' % os.environ['HOME'],
															   'ASS file (*.ass)')
			if not fileName: return
			assFilename = fileName

		self.__traverseAndSaveAssFile(assFilename)
		self.openFilename = assFilename

	def __traverseAndSaveAssFile(self, assFilename):
		AiBegin()
		nodes = Nodegraph.getNodes()
		for node in nodes:
			aNode = AiNode(node.getType())
			AiNodeSetStr(aNode, "name", node.getName())

		for node in nodes:
			aInputNode = AiNodeLookUpByName(node.getName())
			inputs = node.getInputPorts()
			for inputName, input in inputs.iteritems():
				connectedPorts = input.getConnectedPorts()
				for outputPort in connectedPorts:
					outputNode = outputPort.getNode()
					aOutputNode = AiNodeLookUpByName(outputNode.getName())

					a = AiNodeGetArray(aInputNode, inputName)
					AiArraySetPtr(a, 0, aOutputNode)

		AiASSWrite(assFilename, AI_NODE_ALL, False)
		AiEnd()

	def openAssFile(self, assFilename=None, preview=False):
		if assFilename is None:
			fileName, desc = QtGui.QFileDialog.getOpenFileName(self, 'Open file', '%s' % os.environ['HOME'],
															   'ASS file (*.ass)')
			if not fileName: return
			assFilename = fileName

		if self.openFilename:
			self.new()

		self.__loadAndPopulateAssFile(assFilename, preview)
		Events.processEvents()
		window.nodeGraphPanel.nodeGraphView.positionNodes() # TODO: Refactor using Events
		self.openFilename = assFilename

	def __loadAndPopulateAssFile(self, assFilename, preview=False):
		AiBegin()
		AiASSLoad(assFilename)
		nodeIter = AiUniverseGetNodeIterator(AI_NODE_ALL)
		while not AiNodeIteratorFinished(nodeIter):
			node = AiNodeIteratorGetNext(nodeIter)
			nodeEntry = AiNodeGetNodeEntry(node)

			nodeName = AiNodeGetName(node)
			nodeType = AiNodeEntryGetName(nodeEntry)
			nodeBaseType = AiNodeEntryGetTypeName(nodeEntry)
			if nodeName == 'root': continue

			newNode = Nodegraph.createNode(nodeType, nodeName, addRegisteredPorts=not preview)

			outputType = AiNodeEntryGetOutputType(nodeEntry)
			if outputType != AI_TYPE_NONE:
				outputTypeName = AiParamGetTypeName(outputType)
				newNode.addOutputPort(outputTypeName)
			else:
				if nodeType != 'options':
					newNode.addOutputPort('out')

			paramIter = AiNodeEntryGetParamIterator(nodeEntry)
			while not AiParamIteratorFinished(paramIter):
				param = AiParamIteratorGetNext(paramIter)
				paramName = AiParamGetName(param)
				paramType = AiParamGetType(param)
				paramTypeName = AiParamGetTypeName(paramType)

				defaultValue = AiParamGetDefault(param)

				nodeParam = newNode.getParameter(paramName)

				if paramType == AI_TYPE_NODE:
					newPort = newNode.addInputPort(paramName)
					# TODO: Connect ports

				elif paramType == AI_TYPE_ARRAY:
					paramArray = AiNodeGetArray(node, paramName)
					arrayType = AiArrayGetType(paramArray)
					arrayTypeName = AiParamGetTypeName(arrayType)
					if arrayType == AI_TYPE_NODE:
						newPort = newNode.addInputPort(paramName)

						numElems = AiArrayGetNumElements(paramArray)
						for index in range(numElems):
							connectedNode = cast(AiArrayGetPtr(paramArray, index), POINTER(AtNode))
							connectedNodeEntry = AiNodeGetNodeEntry(connectedNode)
							connectedNodeName = AiNodeGetName(connectedNode)
							connectedNodeType = AiNodeEntryGetTypeName(connectedNodeEntry)

							# Check which output port we're connected to
							# If there is only one node output then there's no ambiguity
							connectedNodeOutputType = AiNodeEntryGetOutputType(connectedNodeEntry)
							if connectedNodeOutputType == AI_TYPE_NONE:
								# Maybe we're trying to connect to a node with no defined outputs but
								# the node itself is the output, e.g. a light filter or camera so we
								# define the output as 'out' to give it a chance to connect
								portOutName = 'out'
							elif connectedNodeOutputType != AI_TYPE_ARRAY:
								portOutName = AiParamGetTypeName(connectedNodeOutputType)
							else:
								# TODO: Resolve ambiguity if the node has multiple outputs (array)
								portOutName = 'out'

							Events.queuePostEvent('port_connect',
												  nodeFrom=connectedNodeName, nodeTo=nodeName,
												  portIn=paramName, portOut=portOutName)

				elif paramType == AI_TYPE_FLOAT:
					paramValue = AiNodeGetFlt(node, paramName)
					# self.parameterPanel.addField('string', paramName, '', str(defaultValue.contents.FLT))
					# newNode.setParameter(paramName, paramType, str(defaultValue.contents.FLT), paramValue)
				elif paramType == AI_TYPE_STRING:
					paramValue = AiNodeGetStr(node, paramName)
					nodeParam.value = paramValue
					# self.parameterPanel.addField('string', paramName, '', str(defaultValue.contents.FLT))
					# newNode.setParameter(paramName, paramType, str(defaultValue.contents.STR), paramValue)

				# print nodeName, paramName
				if AiNodeIsLinked(node, paramName):
					newPort = newNode.addInputPort(paramName)

					# TODO: Multiple output ports support (array)
					connectedNode = AiNodeGetLink(node, paramName)
					connectedNodeName = AiNodeGetName(connectedNode)

					# Check which output port we're connected to
					# If there is only one node output then there's no ambiguity
					# Note: This should be refactored into a utility function as it's the same as above
					connectedNodeEntry = AiNodeGetNodeEntry(connectedNode)
					connectedNodeOutputType = AiNodeEntryGetOutputType(connectedNodeEntry)
					if connectedNodeOutputType != AI_TYPE_ARRAY:
						portOutName = AiParamGetTypeName(connectedNodeOutputType)
					else:
						# TODO: Resolve ambiguity if node has multiple outputs (array)
						portOutName = 'out'

					Events.queuePostEvent('port_connect',
										  nodeFrom=connectedNodeName, nodeTo=nodeName,
										  portIn=paramName, portOut=portOutName)

		AiNodeIteratorDestroy(nodeIter)
		AiEnd()


if __name__ == '__main__':
	app = QtGui.QApplication(sys.argv)
	app.setStyle('plastique')

	window = NodeWindow()
	window.show()
	window.raise_()
	window.setFocus()

	sys.exit(app.exec_())