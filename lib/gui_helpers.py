import os
import datetime

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import numpy as np

from andor_helpers import *

layout_params = {
	'main': [1000, 700],
	'image': [700,500],
	'figure': [6, 6]
}

# Config form for user input for setting up acquisition parameters
class ConfigForm(QtGui.QWidget):
	# Initialize
	def __init__(self, Parent=None):
		super(ConfigForm, self).__init__(Parent)
		# Populate form widgets
		self.populate()
		# Set default values for config form entries
		self.setDefaultValues()

	# These default parameters are set in the default_config dict in andor_helpers.py
	def setDefaultValues(self):
		self.exposureEdit.setText(default_config['exposure'])

		self.xOffsetEdit.setText(default_config['xOffset'])
		self.yOffsetEdit.setText(default_config['yOffset'])

		self.dxEdit.setText(default_config['dx'])
		self.dyEdit.setText(default_config['dy'])

		self.binningControl.setChecked(default_config['binning'])

		self.emGainEdit.setText(default_config['emGain'])
		self.emEnableControl.setChecked(default_config['emEnable'])
		self.emGainToggle()

		# Default save path is built off of the default_config save path
		# plus the current date
		now = datetime.datetime.now()
		savedir = now.strftime(default_config['savePath'] + '%Y%m%d\\')
		self.savePathEdit.setText(savedir)

		# Check directory
		# If directory doesn't exist, make it
		# If directory does exist, automatically set the file number to be 1 greater than
		# the last file in the directory
		self.checkDir()

	# Check save directory and file number
	# using path defined in the save path field
	def checkDir(self):
		fileNumber = 0
		savedir = str(self.savePathEdit.text())

		# Check if the directory exists
		if os.path.isdir(savedir):
			filelist = os.listdir(savedir)
			for file in filelist:
				# Extract the file number
				# Files are saved as KRBCAM_FILENAME_BASE + filenumber + kinetics index + .csv
				# where kinetics index is a, b, etc. to number the images in the kinetics series
				# e.g., a possible file number is iXon_img10a.csv
				ind1 = len(KRBCAM_FILENAME_BASE)
				ind2 = file.find('.csv') - 1 # minus 1 to get rid of kinetics index
				
				# Compare file number, if it's bigger than set fileNumber to 1 greater than that
				try:
					substr = file[ind1:ind2]
					num = int(substr)
					if num >= fileNumber:
						fileNumber = num + 1
				except:
					pass
		# If not, make the directory
		else:
			os.makedirs(savedir)
		# Update the file number field of the config form
		self.fileNumberEdit.setText(str(fileNumber))

	# Returns the form data
	# If any field has an invalid format, the default values are reset
	def getFormData(self):
		self.checkDir()
		try:
			form = {}
			form['expTime'] = float(self.exposureEdit.text())
			form['xOffset'] = int(self.xOffsetEdit.text())
			form['yOffset'] = int(self.yOffsetEdit.text())
			form['dx'] = int(self.dxEdit.text())
			form['dy'] = int(self.dyEdit.text())
			form['binning'] = bool(self.binningControl.isChecked())
			form['emEnable'] = bool(self.emEnableControl.isChecked())
			form['emGain'] = int(self.emGainEdit.text())
			form['fileNumber'] = int(self.fileNumberEdit.text())
			form['savePath'] = str(self.savePathEdit.text())
			return form
		except:
			self.throwErrorMessage("Invalid form data!", "Setting default values.")
			self.setDefaultValues()
			return self.getFormData()

	# Takes form as an input dict (should have same keys as gConfig in the main GUI)
	# and populates the form fields with these
	def setFormData(self, form):
		self.exposureEdit.setText(str(form['expTime']))
		self.xOffsetEdit.setText(str(form['xOffset']))
		self.yOffsetEdit.setText(str(form['yOffset']))
		self.dxEdit.setText(str(form['dx']))
		self.dyEdit.setText(str(form['dy']))
		self.binningControl.setChecked(bool(form['binning']))
		self.emEnableControl.setChecked(bool(form['emEnable']))
		self.emGainEdit.setText(str(form['emGain']))
		self.fileNumberEdit.setText(str(form['fileNumber']))
		self.savePathEdit.setText(form['savePath'])

	# If the EM enable box is checked, then enable the EM gain field
	# Otherwise, disable the EM gain field
	def emGainToggle(self):
		try:
			if self.emEnableControl.isChecked():
				self.emGainEdit.setDisabled(False)
				self.emGainEdit.setText("1")
			else:
				self.emGainEdit.setText("0")
				self.emGainEdit.setDisabled(True)
				self.emGainEdit.setStyleSheet("color: rgb(0,0,0);")
		except:
			self.emGainEdit.setText("0")
			self.emGainEdit.setDisabled(True)
			self.emGainEdit.setStyleSheet("color: rgb(0,0,0);")

	# Populate the form with widgets
	def populate(self):
		self.acquireStatic = QtGui.QLabel("Acquire Mode", self)
		self.acquireEdit = QtGui.QLineEdit(self)
		self.acquireEdit.setText("Fast Kinetics")
		self.acquireEdit.setDisabled(True)
		self.acquireEdit.setStyleSheet("color: rgb(0,0,0);")

		self.triggerStatic = QtGui.QLabel("Trigger Mode", self)
		self.triggerEdit = QtGui.QLineEdit(self)

		if KRBCAM_TRIGGER_MODE == 0:
			self.triggerEdit.setText("Internal")
		else:
			self.triggerEdit.setText("External")
		self.triggerEdit.setDisabled(True)
		self.triggerEdit.setStyleSheet("color: rgb(0,0,0);")

		self.exposureStatic = QtGui.QLabel("Exposure (ms)", self)
		self.exposureEdit = QtGui.QLineEdit(self)

		self.emGainStatic = QtGui.QLabel("EM Gain", self)
		self.emGainEdit = QtGui.QLineEdit(self)

		self.emEnableStatic = QtGui.QLabel("EM Enable?", self)
		self.emEnableControl = QtGui.QCheckBox(self)
		self.emEnableControl.stateChanged.connect(self.emGainToggle)

		self.xOffsetStatic = QtGui.QLabel("X Offset (px)", self)
		self.xOffsetEdit = QtGui.QLineEdit(self)
		
		self.yOffsetStatic = QtGui.QLabel("Y Offset (px)", self)
		self.yOffsetEdit = QtGui.QLineEdit(self)
		
		self.dxStatic = QtGui.QLabel("Width dx (px)", self)
		self.dxEdit = QtGui.QLineEdit(self)
		
		self.dyStatic = QtGui.QLabel("Height dy (px)", self)
		self.dyEdit = QtGui.QLineEdit(self)

		self.binningStatic = QtGui.QLabel("Bin 2x2?", self)
		self.binningControl = QtGui.QCheckBox(self)

		self.savePathStatic = QtGui.QLabel("Save to:", self)
		self.savePathEdit = QtGui.QLineEdit(self)

		self.fileNumberStatic = QtGui.QLabel("File number:", self)
		self.fileNumberEdit = QtGui.QLineEdit(self)
		
		self.layout = QtGui.QGridLayout()

		self.layout.addWidget(self.acquireStatic, 1, 0)
		self.layout.addWidget(self.acquireEdit, 1, 1)

		self.layout.addWidget(self.triggerStatic, 2, 0)
		self.layout.addWidget(self.triggerEdit, 2, 1)

		self.layout.addWidget(self.exposureStatic, 3, 0)
		self.layout.addWidget(self.exposureEdit, 3, 1)

		self.layout.addWidget(self.emEnableStatic, 4, 0)
		self.layout.addWidget(self.emEnableControl, 4, 1)

		self.layout.addWidget(self.emGainStatic, 5, 0)
		self.layout.addWidget(self.emGainEdit, 5, 1)

		self.layout.addWidget(QtGui.QLabel(""), 6, 0)

		self.layout.addWidget(self.xOffsetStatic, 7, 0)
		self.layout.addWidget(self.xOffsetEdit, 7, 1)

		self.layout.addWidget(self.yOffsetStatic, 8, 0)
		self.layout.addWidget(self.yOffsetEdit, 8, 1)

		self.layout.addWidget(self.dxStatic, 9, 0)
		self.layout.addWidget(self.dxEdit, 9, 1)

		self.layout.addWidget(self.dyStatic, 10, 0)
		self.layout.addWidget(self.dyEdit, 10, 1)

		self.layout.addWidget(self.binningStatic, 11, 0)
		self.layout.addWidget(self.binningControl, 11, 1)

		self.layout.addWidget(QtGui.QLabel(""), 12, 0)

		self.layout.addWidget(self.savePathStatic, 13, 0)
		self.layout.addWidget(self.savePathEdit, 13, 1)

		self.layout.addWidget(self.fileNumberStatic, 14, 0)
		self.layout.addWidget(self.fileNumberEdit, 14, 1)

		self.setLayout(self.layout)

	# Convenient function for throwing error messages
	def throwErrorMessage(self, header, msg):
		messageBox = QtGui.QMessageBox()
		messageBox.setText(header)
		messageBox.setInformativeText(msg)
		messageBox.exec_()


# Acquire button, abort button, status log
class AcquireAbortStatus(QtGui.QWidget):

	def __init__(self, Parent=None):
		super(AcquireAbortStatus, self).__init__(Parent)
		self.populate()
		self.setDefaultValues()

	# Set default values
	def setDefaultValues(self):
		self.acquireControl.setDisabled(False)
		self.abortControl.setDisabled(True)
		self.statusEdit.setText("Python GUI initialized.\n")

	# Enable abort, disable acquire
	def acquire(self):
		self.acquireControl.setDisabled(True)
		self.abortControl.setDisabled(False)

	# Enable acquire, disable abort
	def abort(self):
		self.abortControl.setDisabled(True)
		self.acquireControl.setDisabled(False)

	# Populate the GUI
	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.acquireControl = QtGui.QPushButton("Update parameters and acquire")
		self.abortControl = QtGui.QPushButton("Stop acquiring")

		self.statusStatic = QtGui.QLabel("Status log:")
		self.statusEdit = QtGui.QTextEdit()
		self.statusEdit.setReadOnly(True)
		self.statusEdit.setStyleSheet("color: rgb(0,0,0);")

		self.layout.addWidget(self.acquireControl)
		self.layout.addWidget(self.abortControl)
		self.layout.addWidget(self.statusStatic)
		self.layout.addWidget(self.statusEdit)

		self.setLayout(self.layout)

# Form for inputting and monitoring cooling status and parameters
class CoolerControl(QtGui.QWidget):

	def __init__(self, Parent=None):
		super(CoolerControl, self).__init__(Parent)
		self.populate()
		self.setDefaultValues()

	# Set default values
	def setDefaultValues(self):
		self.coolerOffControl.setChecked(True)
		self.coolerOff()
		self.coolerStatusEdit.setText("Off")
		self.ccdTempRangeEdit.setText("No camera")
		self.ccdCurrentTempEdit.setText("Cooler off")
		self.ccdSetTempEdit.setText(str(KRBCAM_DEFAULT_TEMP))

	# Given the camInfo dict from the main GUI,
	# display the allowed temp range for the camera
	def setTempRange(self, info):
		mintemp = info['temperatureRange'][0]
		maxtemp = info['temperatureRange'][1]

		msg = "{} to {}".format(mintemp, maxtemp)
		self.ccdTempRangeEdit.setText(msg)

	# Disable On button, enable Off button
	def coolerOn(self):
		self.coolerOnControl.setDisabled(True)
		self.coolerOffControl.setDisabled(False)

	# Disable Off button, enable On button
	def coolerOff(self):
		self.coolerOnControl.setDisabled(False)
		self.coolerOffControl.setDisabled(True)

	# Populate the GUI
	def populate(self):
		self.buttonGroup = QtGui.QButtonGroup(self)

		self.coolerOnControl = QtGui.QRadioButton("On", self)
		self.coolerOffControl = QtGui.QRadioButton("Off", self)

		self.coolerOnControl.clicked.connect(self.coolerOn)
		self.coolerOffControl.clicked.connect(self.coolerOff)

		self.buttonGroup.addButton(self.coolerOnControl)
		self.buttonGroup.addButton(self.coolerOffControl)

		self.buttonGroupLabel = QtGui.QLabel("Cooler control:", self)

		self.coolerStatusStatic = QtGui.QLabel("Cooler Status:", self)
		self.coolerStatusEdit = QtGui.QLineEdit(self)
		self.coolerStatusEdit.setDisabled(True)
		self.coolerStatusEdit.setStyleSheet("color: rgb(0,0,0);")

		self.ccdTempRangeStatic = QtGui.QLabel("Temp. Range (C):", self)
		self.ccdTempRangeEdit = QtGui.QLineEdit(self)
		self.ccdTempRangeEdit.setDisabled(True)
		self.ccdTempRangeEdit.setStyleSheet("color: rgb(0,0,0);")

		self.ccdSetTempStatic = QtGui.QLabel("Set Temp. (C):", self)
		self.ccdSetTempEdit = QtGui.QLineEdit(self)

		self.ccdCurrentTempStatic = QtGui.QLabel("CCD Temp. (C):", self)
		self.ccdCurrentTempEdit = QtGui.QLineEdit(self)
		self.ccdCurrentTempEdit.setDisabled(True)
		self.ccdCurrentTempEdit.setStyleSheet("color: rgb(0,0,0);")

		self.layout = QtGui.QGridLayout()

		self.layout.addWidget(self.buttonGroupLabel, 0, 0)
		self.layout.addWidget(self.coolerOnControl, 1, 0)
		self.layout.addWidget(self.coolerOffControl, 1, 1)
		self.layout.addWidget(self.coolerStatusStatic, 2, 0)
		self.layout.addWidget(self.coolerStatusEdit, 2, 1)
		self.layout.addWidget(self.ccdTempRangeStatic, 3, 0)
		self.layout.addWidget(self.ccdTempRangeEdit, 3, 1)
		self.layout.addWidget(self.ccdSetTempStatic, 4, 0)
		self.layout.addWidget(self.ccdSetTempEdit, 4, 1)
		self.layout.addWidget(self.ccdCurrentTempStatic, 5, 0)
		self.layout.addWidget(self.ccdCurrentTempEdit, 5, 1)

		self.setLayout(self.layout)

# Window for displaying images after they are acquired
class ImageWindow(QtGui.QWidget):
	def __init__(self, Parent=None):
		super(ImageWindow, self).__init__(Parent)
		self.setFixedSize(layout_params['image'][0],layout_params['image'][1])
		self.populate()
		self.setDefaultValues()

	def setDefaultValues(self):
		self.kSelectButton.setChecked(True)

	# Populate GUI
	# self.displayData is a listener for any state change of the buttons
	def populate(self):
		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.toolbar = NavigationToolbar(self.canvas, self)

		self.buttonGroup = QtGui.QButtonGroup(self)
		self.kSelectButton = QtGui.QRadioButton("K", self)
		self.rbSelectButton = QtGui.QRadioButton("Rb", self)
		self.buttonGroup.addButton(self.kSelectButton)
		self.buttonGroup.addButton(self.rbSelectButton)
		self.buttonGroup.buttonClicked.connect(self.displayData)

		self.frameSelect = QtGui.QComboBox(self)
		self.frameSelect.addItem("OD")
		self.frameSelect.addItem("Shadow")
		self.frameSelect.addItem("Light")
		self.frameSelect.addItem("Dark")
		self.frameSelect.currentIndexChanged.connect(self.displayData)

		self.layout = QtGui.QGridLayout()
		self.layout.addWidget(self.toolbar,0,0,1,4)
		self.layout.addWidget(self.canvas,1,0,4,4)
		self.layout.addWidget(self.kSelectButton,5,0)
		self.layout.addWidget(self.rbSelectButton,5,1)
		self.layout.addWidget(self.frameSelect,5,2,1,2)

		self.setLayout(self.layout)

	# Display the data!
	def displayData(self):
		# Take the button states and determine what image the user wants to see
		(fk, od) = self.getConfig()

		# Then try to plot the image
		try:
			self.plot(self.data[fk][od])
		# AttributeError will occur if no data collected, since
		# then self.data is undefined
		except AttributeError:
			pass

	# Determine which image to display
	def getConfig(self):
		if self.kSelectButton.isChecked():
			fk = 0
		else:
			fk = 1
		od = self.frameSelect.currentIndex()
		if od == -1:
			od = 0
		return (fk, od)

	# Load in the data
	# Currently this is a bit clunky
	# The main GUI handles saving the data to csv file
	# The ImageWindow then opens the csv file and re-imports the data
	def loadData(self, folder, fileNumber):
		data = []

		# Each shot in the kinetic series has a different filenumber
		for i in range(KRBCAM_FK_SERIES_LENGTH):
			od_series = []
			path = folder + KRBCAM_FILENAME_BASE + str(fileNumber) + chr(ord('a') + i) + ".csv"
			
			# Read the data into a numpy array
			with open(path, 'r') as f:
				arr = np.loadtxt(f, delimiter=',', skiprows=0)
				
				# Each file has OD_SERIES_LENGTH images in it
				# (i.e., shadow, light, and dark frames)
				# Need to separate into distinct arrays
				num_images = KRBCAM_OD_SERIES_LENGTH
				(length, x) = np.shape(arr)
				length = length / num_images
				for j in range(num_images):
					od_series.append(arr[i*length:(i+1)*length - 1, : ])

			# Calculate OD of the image assuming no saturation
			shadow = od_series[0] - od_series[2]
			background = od_series[1] - od_series[2]
			with np.errstate(divide='ignore', invalid='ignore'):
				od = np.log(background / shadow)
				od[od == np.inf] = 0
			od_series = [od] + od_series
			data.append(od_series)

		# Store data
		# Data is a 2-index array
		# First index runs over kinetic series
		# Second index runs over OD series
		self.data = data

	# Plot the data
	def plot(self, data):
		# Clear plot
		self.figure.clear()

		# Plot the data
		ax = self.figure.add_subplot(111)
		im = ax.imshow(data)

		# Add a horizontal colorbar
		self.figure.colorbar(im, orientation='horizontal')

		# Need to do the following to get the z data to show up in the toolbar
		numrows, numcols = np.shape(data)
		def format_coord(x, y):
		    col = int(x + 0.5)
		    row = int(y + 0.5)
		    if col >= 0 and col < numcols and row >= 0 and row < numrows:
		        z = data[row, col]
		        # return 'x=%1.4f, y=%1.4f, z=%1.4f' % (x, y, z)
		        return '({:},{:}), z={:.2f}'.format(int(x),int(y),z)
		    else:
		        return 'x=%1.4f, y=%1.4f' % (x, y)
		ax.format_coord = format_coord

		# Update the plot
		self.canvas.draw()