from abc import ABCMeta, abstractproperty
from arnold import *
import Events

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Parameter:
	def __init__(self, name, type, default, value=None, hints={}):
		self.name = name
		self.type = type
		self.default = default
		self.value = value
		self.hints = hints

	def getName(self):
		return self.name

	def getType(self):
		return self.type

	def getDefault(self):
		return self.default

	def getValue(self):
		return self.value

	def getHints(self):
		return self.hints


class Port:
	def __init__(self, name, type, node):
		self.name = name
		self.type = type
		self.node = node
		self.connectedPorts = []

	def getName(self):
		return self.name

	def getType(self):
		return self.type

	def getNode(self):
		return self.node

	def getConnectedPorts(self):
		return self.connectedPorts

	def connect(self, port):
		if port.getType == self.getType() or port.getNode().getName() == self.getNode().getName(): return
		if port in self.connectedPorts: return

		self.connectedPorts.append(port)
		port.connectedPorts.append(self)

		if self.getType() == 'in':
			nodeFrom, nodeTo = port.getNode().getName(), self.getNode().getName()
			portIn, portOut = self.getName(), port.getName()
		else:
			nodeFrom, nodeTo = self.getNode().getName(), port.getNode().getName()
			portIn, portOut = port.getName(), self.getName()

		Events.queuePostEvent('port_connect', nodeFrom=nodeFrom, nodeTo=nodeTo, portIn=portIn, portOut=portOut)


class Node(object):
	# __metaclass__ = ABCMeta

	def __init__(self, parent=None):
		self.parameters = {}
		self.inputPorts = {}
		self.outputPorts = {}

		self.properties = {}
		# self.properties.setdefault('position', (0, 0))

	# @abstractproperty
	# def type(self): return
	# @abstractproperty
	# def baseType(self): return

	def addRegisteredPorts(self):
		for portName in self.registeredInputPorts:
			self.addInputPort(portName)

		for portName in self.registeredOutputPorts:
			self.addOutputPort(portName)

	def addRegisteredParameters(self):
		for param in self.registeredParameters:
			self.parameters[param.getName()] = param

	def setName(self, name):
		self.name = name

	def getName(self):
		return self.name

	def getType(self):
		return self.type

	def getBaseType(self):
		return self.baseType

	def setParameter(self, name, type, default, value=None, hints={}):
		self.parameters[name] = Parameter(name, type, default, value)

	def getParameters(self):
		return self.parameters

	def getParameter(self, name):
		if name not in self.parameters: return None
		return self.parameters[name]

	def addInputPort(self, name):
		if name in self.inputPorts: return
		port = self.inputPorts[name] = Port(name, 'in', self)
		Events.queueEvent('node_addInputPort', node=self, portName=name)
		return port

	def addOutputPort(self, name):
		if name in self.outputPorts: return
		port = self.outputPorts[name] = Port(name, 'out', self)
		Events.queueEvent('node_addOutputPort', node=self, portName=name)
		return port

	def getInputPort(self, name):
		if name in self.inputPorts: return self.inputPorts[name]
		return None

	def getInputPorts(self):
		return self.inputPorts

	def getOutputPort(self, name):
		if name in self.outputPorts: return self.outputPorts[name]
		return None

	def getOutputPorts(self):
		return self.outputPorts

	# NOTE: Remove, rename ports

# Node.register(tuple)

def __processParam(parameters, param):
	paramName = AiParamGetName(param)
	paramType = AiParamGetType(param)
	paramTypeName = AiParamGetTypeName(paramType)
	defaultValue = AiParamGetDefault(param)
	hints = {}

	if paramType == AI_TYPE_STRING:
		parameters.append(Parameter(paramName, paramTypeName, str(defaultValue.contents.STR)))
	elif paramType == AI_TYPE_INT:
		parameters.append(Parameter(paramName, paramTypeName, int(defaultValue.contents.INT)))
	elif paramType == AI_TYPE_FLOAT:
		parameters.append(Parameter(paramName, paramTypeName, float(defaultValue.contents.FLT)))
	elif paramType == AI_TYPE_BOOLEAN:
		parameters.append(Parameter(paramName, paramTypeName, bool(defaultValue.contents.BOOL)))
	elif paramType == AI_TYPE_ENUM:
		enum = AiParamGetEnum(param)
		value = str(enum.contents.value)

		# Note: Surely there's a way to get the enum values more efficiently
		enumOptions = []
		n = 0
		while AiEnumGetString(enum, n) is not None:
			enumOptions.append(AiEnumGetString(enum, n))
			n += 1

		hints['enum_options'] = enumOptions
		parameters.append(Parameter(paramName, paramTypeName, value, hints=hints))

def __registerNodes():
	logger.info('Registering Arnold Nodes')
	registeredNodes = {}

	AiBegin()
	nodeIter = AiUniverseGetNodeEntryIterator(AI_NODE_ALL)
	while not AiNodeEntryIteratorFinished(nodeIter):
		node = AiNodeEntryIteratorGetNext(nodeIter)
		nodeName = AiNodeEntryGetName(node)
		nodeType = AiNodeEntryGetTypeName(node)

		inputPorts = []
		outputPorts = []
		parameters = []

		# Determine the outputs for this node
		outputType = AiNodeEntryGetOutputType(node)
		if outputType != AI_TYPE_NONE:
			outputTypeName = AiParamGetTypeName(outputType)
			outputPorts.append(outputTypeName)
		else:
			if nodeType != 'options':
				outputPorts.append('out')

		# Determine the inputs for this node.
		# For non-shader nodes we currently only consider node connections.
		# Note: Can we connect to any input on a non-shader node in Arnold (e.g. noise)?
		# For shader nodes we should probably add all the parameters as inputs as
		# any connected node can procedurally tweak a shader parameter.
		paramIter = AiNodeEntryGetParamIterator(node)
		while not AiParamIteratorFinished(paramIter):
			param = AiParamIteratorGetNext(paramIter)
			paramName = AiParamGetName(param)
			paramType = AiParamGetType(param)
			paramTypeName = AiParamGetTypeName(paramType)

			defaultValue = AiParamGetDefault(param)

			if nodeType == 'shader':
				if paramType in (AI_TYPE_RGB, AI_TYPE_RGBA, AI_TYPE_FLOAT):
					inputPorts.append(paramName)

				__processParam(parameters, param)
			else:
				if paramType == AI_TYPE_NODE:
					inputPorts.append(paramName)

				elif paramType == AI_TYPE_ARRAY:
					paramArray = AiParamGetDefault(param).contents.ARRAY
					arrayType = AiArrayGetType(paramArray)
					arrayTypeName = AiParamGetTypeName(arrayType)
					if arrayType == AI_TYPE_NODE:
						inputPorts.append(paramName)

				__processParam(parameters, param)

		classDict = {
			'name': nodeName, 'type': nodeName, 'baseType': nodeType,
			'registeredInputPorts': inputPorts, 'registeredOutputPorts': outputPorts,
			'registeredParameters': parameters
		}
		registeredNodes[nodeName] = {
			'class': type(nodeName, (Node,), classDict),
			'name': nodeName, 'type': nodeName, 'baseType': nodeType
		}

	AiNodeEntryIteratorDestroy(nodeIter)
	AiEnd()

	return registeredNodes

__registeredNodes = __registerNodes()
__nodes = {}

def createNode(type, name=None, deferred=True, addRegisteredPorts=True):
	if type not in __registeredNodes:
		logger.warning('Could not find node %s in registry' % type)
		return

	node = __registeredNodes[type]['class']()
	if not name: name = type
	node.setName(name)
	__nodes[name] = node
	Events.queueEvent('node_create', node=node)

	if addRegisteredPorts: node.addRegisteredPorts()
	node.addRegisteredParameters()

	if not deferred: Events.processEvents()
	return node

def getNode(name):
	if name in __nodes:
		return __nodes[name]

	return None

def getNodes():
	return __nodes.values()

def clearNodes():
	global __nodes
	__nodes = {}
	Events.queueEvent('node_clear')

def getRegisteredNodes():
	return __registeredNodes

def getRegisteredNode(name):
	if name not in __registeredNodes:
		logger.error('Node %s not registered' % name)
		return None

	return __registeredNodes[name]


# Note: Not sure about this
def __portConnect(nodeFrom, nodeTo, portIn, portOut):
	nodeOut = getNode(nodeFrom)
	nodeIn = getNode(nodeTo)

	if nodeOut is None: return
	if nodeIn is None: return

	input = nodeIn.getInputPort(portIn)
	output = nodeOut.getOutputPort(portOut)

	output.connect(input)

Events.registerHandler(__portConnect, 'port_connect')
