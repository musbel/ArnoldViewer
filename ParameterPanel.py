import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

import Events
import Nodegraph


# class ParameterPanel(QtGui.QWidget):
class ParameterPanel(QtGui.QFrame):
	def __init__(self, parent):
		super(ParameterPanel, self).__init__(parent)
		self.setMinimumSize(250, 250)
		self.setMaximumSize(500, 500)

		QtGui.QVBoxLayout(self)
		self.layout().setContentsMargins(0, 0, 0, 0)
		self.layout().setSpacing(0)

		# Add navigation arrows
		hbox = QtGui.QHBoxLayout()
		hbox.setContentsMargins(0, 0, 0, 0)
		hbox.setSpacing(0)

		self.layout().addLayout(hbox, 0)

		self.__panelScrollArea = PanelScrollArea(self)
		self.layout().addWidget(self.__panelScrollArea, 10)

		Events.registerHandler(self.__selectNode, 'node_select')

	def __selectNode(self, names):
		self.__panelScrollArea.initialise()

		# We only show parameters for one node at the moment
		if len(names) != 1:
			return

		# Get the node container
		nodeName = names[0]
		node = Nodegraph.getNode(nodeName)
		if node is None:
			raise Exception('Node %s not found in Node Graph container' % nodeName)
			return

		self.__panelScrollArea.addParameters(node)


class PanelScrollArea(QtGui.QScrollArea):
	def __init__(self, parent=None):
		self.parent = parent
		self.fields = {}
		QtGui.QScrollArea.__init__(self, parent)

		self.initialise()

	def initialise(self):
		self.scrollParent = QtGui.QWidget(self)
		self.setWidget(self.scrollParent)
		self.setWidgetResizable(True)
		self.setFrameStyle(self.NoFrame + self.Plain)

		self.gridLayout = QtGui.QGridLayout(self)
		self.gridLayout.setAlignment(QtCore.Qt.AlignTop)
		self.scrollParent.setLayout(self.gridLayout)

	def addParameters(self, node):
		# Our preference is to add the type and name at the top (and ignore these parameters below)
		qTypeLabel = QtGui.QLabel('type')
		qTypeText = QtGui.QLabel(node.getType())
		self.gridLayout.addWidget(qTypeLabel, 0, 0)
		self.gridLayout.addWidget(qTypeText, 0, 1)

		self.separator = QtGui.QFrame(self)
		self.separator.setEnabled(True)
		self.separator.setFrameShape(QtGui.QFrame.HLine)
		self.separator.setFrameShadow(QtGui.QFrame.Sunken)
		self.gridLayout.addWidget(self.separator, 1, 0, 1, 2)

		qNameLabel = QtGui.QLabel('name')
		qNameText = QtGui.QLineEdit(node.getName())
		self.gridLayout.addWidget(qNameLabel, 2, 0)
		self.gridLayout.addWidget(qNameText, 2, 1)

		parameters = node.getParameters()
		for paramName, param in parameters.iteritems():
			if paramName in ('type', 'name'): continue # We've already created these above
			type = param.getType()
			default = param.getDefault()
			value = param.getValue()
			hints = param.getHints()

			if value is None:
				value = default

			qLabel = QtGui.QLabel(paramName)
			# qLabel.setToolTip(tip)
			qEdit = None

			# print "{} {} {}".format(label, type, value)

			if type == 'STRING' or type == 'FLOAT':
				qEdit = QtGui.QLineEdit()
				qEdit.setText(str(value))
			elif type == 'text':
				qEdit = QtGui.QTextEdit()
				qEdit.setText(str(value))
			elif type == 'BOOL':
				qEdit = QtGui.QCheckBox()
				trues = [True, 'yes', 'on', 1]
				qEdit.setChecked(value in trues)
			elif type == 'ENUM':
				qEdit = QSelect(self)
				enum_options = hints.get('enum_options', [])
				for item in enum_options:
					qEdit.addItem(item)

				if value is not None:
					qEdit.setCurrentIndex(value if isinstance(value, int) else enum_options.index(value))

			if qEdit is not None:
				qEdit.setFont(QtGui.QFont('tahoma', 10, QtGui.QFont.Normal, 0))
				qEdit.setStyleSheet('color: white')

				numRows = self.gridLayout.rowCount()
				self.gridLayout.addWidget(qLabel, numRows, 0)
				self.gridLayout.addWidget(qEdit, numRows, 1)


class QSelect(QtGui.QComboBox):
	'''Qselect is like a QComboBox, but has correct mouse wheel behaviour (only responds to wheel when it has focus).'''
	def __init__(self, parent=None, options=None, default=None, cb=None):
		QtGui.QComboBox.__init__(self, parent)
		self.setFocusPolicy(QtCore.Qt.StrongFocus)
		if options != None:
			for item in options: self.addItem(item)
			if default != None:
				self.setCurrentIndex(options.index(default))

		self.cb = cb
		self.connect(self, QtCore.SIGNAL('currentIndexChanged(int)'), self.callback)

	def callback(self, val):
		if self.cb != None: self.cb(self, val)

	def wheelEvent(self, e):
		if self.hasFocus():
			QtGui.QComboBox.wheelEvent(self, e)
		else:
			e.ignore()

	def focusInEvent(self, e):
		e.accept()
		self.setFocusPolicy(QtCore.Qt.WheelFocus)
		QtGui.QComboBox.focusInEvent(self, e)

	def focusOutEvent(self, e):
		e.accept()
		self.setFocusPolicy(QtCore.Qt.StrongFocus)
		QtGui.QComboBox.focusOutEvent(self, e)

