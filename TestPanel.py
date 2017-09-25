import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

from NodeGraphics import *
import Nodegraph


class SideBar(QtGui.QFrame):
	def __init__(self, parent):
		super(SideBar, self).__init__(parent)
		self.setObjectName('SideBar')
		self.initUi()

	def initUi(self):
		# Frame
		self.setFixedWidth(200)

		# Central Layout
		self.CentralLayout = QtGui.QVBoxLayout(self)

		# Buttons
		self.AddBoxButton = QtGui.QPushButton('Add Box')
		self.CentralLayout.addWidget(self.AddBoxButton)

		# Connections
		self.initConnections()

	def initConnections(self):
		self.AddBoxButton.clicked.connect(self.clickedAddBoxButton)

	def clickedAddBoxButton(self):
		node = Nodegraph.createNode('polymesh', name='earth')
		node.addInputPort('in')
		node.addOutputPort('out')
		Events.processEvents()
