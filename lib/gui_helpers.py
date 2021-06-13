import os
import datetime

import json

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from matplotlib import pyplot as plt

import numpy as np

from copy import deepcopy

from andor_helpers import *

from krb_custom_colors import KRbCustomColors

layout_params = {
	'main': [1000, 975],
	'image': [700, 700],
	'figure': [6, 6]
}

PATH_TO_LIB = os.path.dirname(os.path.abspath(__file__))
PATH_TO_CONFIG = os.path.join(PATH_TO_LIB, "config/")

# Config form for user input for setting up acquisition parameters
class ConfigForm(QtGui.QWidget):
	# Initialize
	def __init__(self, iw, Parent=None):
		super(ConfigForm, self).__init__(Parent)
		# Populate form widgets
		self.populate()

		# Ugly but for now:
		self.imageWindow = iw

		# Set default values for config form entries
		self.setDefaultValues()

	# These default parameters are set in the default_config dict in andor_helpers.py
	def setDefaultValues(self, config=default_config):
		self.kineticsFramesEdit.setValue(int(config['kinFrames']))
		self.acqLengthEdit.setValue(int(config['acqLength']))

		self.exposureEdit.setText(str(config['expTime']))

		self.xOffsetEdit.setText(str(config['xOffset']))
		self.yOffsetEdit.setText(str(config['yOffset']))

		self.dxEdit.setText(str(config['dx']))
		self.dyEdit.setText(str(config['dy']))

		self.binningControl.setChecked(config['binning'])

		self.emGainEdit.setText(str(config['emGain']))
		self.emEnableControl.setChecked(config['emEnable'])
		self.emGainToggle()

		self.saveEnableControl.setChecked(config['saveFiles'])
		self.saveControlToggle()

		if config.has_key('rotateImage'):
			self.rotateImageControl.setChecked(config['rotateImage'])
		else:
			self.rotateImageControl.setChecked(False)

		if config.has_key('saveNpz'):
			self.saveNpzControl.setChecked(config['saveNpz'])
		else:
			self.saveNpzControl.setChecked(False)

		try:
			self.saveFolderEdit.setText(config['saveFolder'])
			self.fileBaseEdit.setText(config['filebase'])
		except:
			self.saveFolderEdit.setText(KRBCAM_DEFAULT_FOLDER)
			self.fileBaseEdit.setText(KRBCAM_DEFAULT_FILENAME_BASE)
		folder = str(self.saveFolderEdit.text()) + '\\'

		# Default save path is built off of the default_config save path
		# plus the current date
		now = datetime.datetime.now()
		savedir = (default_config['savePath'] + KRBCAM_SAVE_PATH_SUFFIX + folder).format(now)
		self.savePathEdit.setText(savedir)

		# Check directory
		# If directory doesn't exist, make it
		# If directory does exist, automatically set the file number to be 1 greater than
		# the last file in the directory
		self.checkDir()

		# Try to initialize the combo boxes to the right value
		try:
			self.adChannelControl.setCurrentIndex(config['adChannel'])
			self.controlHSSOptions()

			self.hssControl.setCurrentIndex(config['hss'])
			self.preAmpGainControl.setCurrentIndex(config['preAmpGain'])

			self.vssControl.setCurrentIndex(config['vss'])
		# Hit exception if communication with camera isn't setup yet
		except Exception as e:
			pass

		self.imageWindow.controlComboBoxes(int(config['kinFrames']), int(config['acqLength']))
		if config.has_key('fss'):
			self.imageWindow.setFrameSelectState(config['fss'])

	# Check save directory and file number
	# using path defined in the save path field
	def checkDir(self):
		fileNumber = 0
		savedir = str(self.savePathEdit.text())
		folder = str(self.saveFolderEdit.text())
		filebase = str(self.fileBaseEdit.text()) + '_'

		# Last part of the path that includes the date information and the folder
		suffix = deepcopy(KRBCAM_SAVE_PATH_SUFFIX).format(datetime.datetime.now()) + folder + '\\'

		# Verify that the date and folder are correct
		if savedir.find(suffix) == -1:
			# Ensure that we are using the default save path before updating the path
			# If we aren't, then all bets are off and we should just leave the path as is.
			if savedir.find(KRBCAM_DEFAULT_SAVE_PATH) != -1:
				# Update the path in the GUI
				savedir = KRBCAM_DEFAULT_SAVE_PATH + suffix
				self.savePathEdit.setText(savedir)

		# Check if the directory exists
		if os.path.isdir(savedir):
			filelist = os.listdir(savedir)
			for file in filelist:
				# Extract the file number
				# Files are saved as KRBCAM_FILENAME_BASE + filenumber + .csv/.npz
				ind1 = len(filebase)
				if not self.saveNpzControl.isChecked():
					ind2 = file.find('.csv')
				else:
					ind2 = file.find('.npz')
				
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
			try:
				os.makedirs(savedir)
			except WindowsError: # If the drive doesn't exist
				self.throwErrorMessage("Can't set save path to: " + savedir, "Setting default local path.")
				self.savePathEdit.setText(KRBCAM_LOCAL_SAVE_PATH + suffix)
				self.checkDir()

		# Update the file number field of the config form
		self.fileNumberEdit.setText(str(fileNumber))

	# Setup Combo Boxes
	# The items are dependent on the camera capabilities
	def setupComboBoxes(self, config):
		# Get the camera info
		self.hss = config['hss']
		self.hssPA = config['hssPreAmp']
		self.pa = config['preAmpGain']
		self.nADC = config['adChannels']

		# Populate AD Channels
		for i in range(self.nADC):
			self.adChannelControl.addItem(str(i))

		# Populate horizontal shift speeds
		self.controlHSSOptions()

		# Populate vertical shift speeds
		for val in config['vss']:
			self.vssControl.addItem("{:.2} usec".format(val))

	# Setup horizontal shift speed options
	# The items are dependent on the camera capabilities
	def controlHSSOptions(self):
		# Clear combo box
		self.hssControl.clear()

		# Need to know whether we are in EM mode
		if self.emEnableControl.isChecked():
			typ = 0
		else:
			typ = 1

		# Need AD channel
		adc = int(self.adChannelControl.currentIndex())

		# Populate the box
		for val in self.hss[adc][typ]:
			self.hssControl.addItem("{:.1f} MHz".format(val))

		# Populate the pre amp options
		self.controlPAOptions()

	# Setup pre amplifier options
	# The items are dependent on the camera capabilities
	def controlPAOptions(self):
		# Clear the combo box
		self.preAmpGainControl.clear()

		# Need to know whether we are in EM mode
		if self.emEnableControl.isChecked():
			typ = 0
		else:
			typ = 1

		# Get current AD channel and current HSS
		adc = int(self.adChannelControl.currentIndex())
		hss = int(self.hssControl.currentIndex())

		# Populate box, only counting pre amp controls that are available
		# for this HSS
		for i in range(len(self.pa)):
			if self.hssPA[adc][typ][hss][i]:
				self.preAmpGainControl.addItem(str(self.pa[i]))

	# Returns the form data
	# If any field has an invalid format, the default values are reset
	def getFormData(self):
		self.checkDir()
		try:
			form = {}
			form['kinFrames'] = int(self.kineticsFramesEdit.value())
			form['acqLength'] = int(self.acqLengthEdit.value())
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
			form['saveFolder'] = str(self.saveFolderEdit.text())
			form['filebase'] = str(self.fileBaseEdit.text())
			form['vss'] = self.vssControl.currentIndex()
			form['adChannel'] = self.adChannelControl.currentIndex()
			form['hss'] = self.hssControl.currentIndex()
			form['preAmpGain'] = self.preAmpGainControl.currentIndex()
			form['saveFiles'] = bool(self.saveEnableControl.isChecked())
			form['rotateImage'] = bool(self.rotateImageControl.isChecked())
			form['saveNpz'] = bool(self.saveNpzControl.isChecked())
			return form
		except:
			self.throwErrorMessage("Invalid form data!", "Try again.")
			self.setDefaultValues()
			return self.getFormData()

	# Takes form as an input dict (should have same keys as gConfig in the main GUI)
	# and populates the form fields with these
	def setFormData(self, form):
		self.kineticsFramesEdit.setValue(int(form['kinFrames']))
		self.acqLengthEdit.setValue(int(form['acqLength']))
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
		self.saveFolderEdit.setText(form['saveFolder'])
		self.fileBaseEdit.setText(form['filebase'])

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

	# Control labels based on acquisition mode
	def controlAcquireMode(self):
		# if self.acquireEdit.currentIndex() == 0:
		# 	self.vssStatic.setText("VSS Speed")
		# else:
		# 	self.vssStatic.setText("FKVS Speed")

		if int(self.kineticsFramesEdit.value()) == 1:
			self.vssStatic.setText("VSS Speed")
		else:
			self.vssStatic.setText("FKVS Speed")

	# Save files control toggle
	def saveControlToggle(self):
		if self.saveEnableControl.isChecked():
			self.savePathEdit.setDisabled(False)
			self.fileNumberEdit.setDisabled(False)
		else:
			self.savePathEdit.setDisabled(True)
			self.fileNumberEdit.setDisabled(True)

	# Freeze the form when acquisition is in progress
	def freezeForm(self, acquiring):
		# self.acquireEdit.setDisabled(acquiring)

		self.kineticsFramesEdit.setDisabled(acquiring)
		self.acqLengthEdit.setDisabled(acquiring)
		self.exposureEdit.setDisabled(acquiring)
		self.emEnableControl.setDisabled(acquiring)
		self.emGainEdit.setDisabled(acquiring)
		self.adChannelControl.setDisabled(acquiring)
		self.hssControl.setDisabled(acquiring)
		self.preAmpGainControl.setDisabled(acquiring)
		self.xOffsetEdit.setDisabled(acquiring)
		self.yOffsetEdit.setDisabled(acquiring)
		self.dxEdit.setDisabled(acquiring)
		self.dyEdit.setDisabled(acquiring)
		self.binningControl.setDisabled(acquiring)
		self.vssControl.setDisabled(acquiring)
		self.savePathEdit.setDisabled(acquiring)
		self.saveFolderEdit.setDisabled(acquiring)
		self.fileBaseEdit.setDisabled(acquiring)
		self.fileNumberEdit.setDisabled(acquiring)
		self.saveEnableControl.setDisabled(acquiring)
		self.rotateImageControl.setDisabled(acquiring)
		self.saveNpzControl.setDisabled(acquiring)

	def saveConfig(self):
		fileName = QtGui.QFileDialog.getSaveFileName(self, "Save current configuration", PATH_TO_CONFIG, "JSON files (*.json)")

		if fileName != "":
			formData = self.getFormData()

			fss = self.imageWindow.getFrameSelectState()
			formData["fss"] = fss

			formData.pop('savePath', None)
			formData.pop('fileNumber', None)

			with open(fileName, "w") as f:
				json.dump(formData, f, indent=4, sort_keys=True)

	def loadConfig(self):
		fileName = QtGui.QFileDialog.getOpenFileName(self, "Open a configuration", PATH_TO_CONFIG, "JSON files (*.json)")

		if fileName != "":
			with open(fileName, "r") as f:
				configData = json.load(f)
			self.setDefaultValues(configData)

			self.imageWindow.controlComboBoxes(int(configData['kinFrames']), int(configData['acqLength']))
			if configData.has_key("fss"):
				self.imageWindow.setFrameSelectState(configData["fss"])

	# Populate the form with widgets
	def populate(self):
		self.cameraNameStatic = QtGui.QLabel("", self)
		font = self.cameraNameStatic.font()
		font.setPointSize(14)
		font.setBold(True)
		self.cameraNameStatic.setFont(font)

		self.saveConfigControl = QtGui.QPushButton("Save config", self)
		self.saveConfigControl.clicked.connect(self.saveConfig)
		self.loadConfigControl = QtGui.QPushButton("Load config", self)
		self.loadConfigControl.clicked.connect(self.loadConfig)

		self.kineticsFramesStatic = QtGui.QLabel("Fast Kinetics frames", self)
		self.kineticsFramesEdit = QtGui.QSpinBox(self)
		self.kineticsFramesEdit.setRange(1,6)
		self.kineticsFramesEdit.valueChanged.connect(self.controlAcquireMode)

		self.acqLengthStatic = QtGui.QLabel("Acquisition loop length", self)
		self.acqLengthEdit = QtGui.QSpinBox(self)
		self.acqLengthEdit.setRange(1,3)

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
		self.emEnableControl.stateChanged.connect(self.controlHSSOptions)

		self.adChannelStatic = QtGui.QLabel("AD Channel", self)
		self.adChannelControl = QtGui.QComboBox(self)
		self.adChannelControl.currentIndexChanged.connect(self.controlHSSOptions)

		self.hssStatic = QtGui.QLabel("HS Speed", self)
		self.hssControl = QtGui.QComboBox(self)
		self.hssControl.currentIndexChanged.connect(self.controlPAOptions)

		self.preAmpGainStatic = QtGui.QLabel("Pre-Amp Gain", self)
		self.preAmpGainControl = QtGui.QComboBox(self)

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

		if KRBCAM_ACQ_MODE == 4:
			self.vssStatic = QtGui.QLabel("FKVS Speed", self)
		elif KRBCAM_ACQ_MODE == 1:
			self.vssStatic = QtGui.QLabel("VSS Speed", self)
		self.vssControl = QtGui.QComboBox(self)

		self.savePathStatic = QtGui.QLabel("Save data directory:", self)
		self.savePathEdit = QtGui.QLineEdit(self)

		self.saveFolderStatic = QtGui.QLabel("Folder name:", self)
		self.saveFolderEdit = QtGui.QLineEdit(self)

		self.fileBaseStatic = QtGui.QLabel("Filename base:", self)
		self.fileBaseEdit = QtGui.QLineEdit(self)

		self.fileNumberStatic = QtGui.QLabel("File number:", self)
		self.fileNumberEdit = QtGui.QLineEdit(self)

		self.saveEnableStatic = QtGui.QLabel("Save files?", self)
		self.saveEnableControl = QtGui.QCheckBox(self)
		self.saveEnableControl.stateChanged.connect(self.saveControlToggle)

		self.rotateImageStatic = QtGui.QLabel("Rotate image?", self)
		self.rotateImageControl = QtGui.QCheckBox(self)

		self.saveNpzStatic = QtGui.QLabel("Save .npz?", self)
		self.saveNpzControl = QtGui.QCheckBox(self)
		
		self.layout = QtGui.QGridLayout()

		row = 1
		self.layout.addWidget(self.cameraNameStatic, row, 0, 4, 4)
		row += 4
		self.layout.addWidget(self.saveConfigControl, row, 0, 1, 2)
		row += 1
		self.layout.addWidget(self.loadConfigControl, row, 0, 1, 2)
		row += 1

		self.layout.addWidget(QtGui.QLabel(""), row, 0)
		row += 1

		self.layout.addWidget(self.kineticsFramesStatic, row, 0)
		self.layout.addWidget(self.kineticsFramesEdit, row, 1)
		row += 1

		self.layout.addWidget(self.acqLengthStatic, row, 0)
		self.layout.addWidget(self.acqLengthEdit, row, 1)
		row += 1

		self.layout.addWidget(QtGui.QLabel(""), row, 0)
		row += 1

		self.layout.addWidget(self.triggerStatic, row, 0)
		self.layout.addWidget(self.triggerEdit, row, 1)
		row += 1

		self.layout.addWidget(self.exposureStatic, row, 0)
		self.layout.addWidget(self.exposureEdit, row, 1)
		row += 1

		self.layout.addWidget(self.emEnableStatic, row, 0)
		self.layout.addWidget(self.emEnableControl, row, 1)
		row += 1

		self.layout.addWidget(self.emGainStatic, row, 0)
		self.layout.addWidget(self.emGainEdit, row, 1)
		row += 1

		self.layout.addWidget(self.adChannelStatic, row, 0)
		self.layout.addWidget(self.adChannelControl, row, 1)
		row += 1

		self.layout.addWidget(self.hssStatic, row, 0)
		self.layout.addWidget(self.hssControl, row, 1)
		row += 1

		self.layout.addWidget(self.preAmpGainStatic, row, 0)
		self.layout.addWidget(self.preAmpGainControl, row, 1)
		row += 1

		self.layout.addWidget(QtGui.QLabel(""), row, 0)
		row += 1

		self.layout.addWidget(self.xOffsetStatic, row, 0)
		self.layout.addWidget(self.xOffsetEdit, row, 1)
		row += 1

		self.layout.addWidget(self.yOffsetStatic, row, 0)
		self.layout.addWidget(self.yOffsetEdit, row, 1)
		row += 1

		self.layout.addWidget(self.dxStatic, row, 0)
		self.layout.addWidget(self.dxEdit, row, 1)
		row += 1

		self.layout.addWidget(self.dyStatic, row, 0)
		self.layout.addWidget(self.dyEdit, row, 1)
		row += 1

		self.layout.addWidget(self.binningStatic, row, 0)
		self.layout.addWidget(self.binningControl, row, 1)
		row += 1

		self.layout.addWidget(self.vssStatic, row, 0)
		self.layout.addWidget(self.vssControl, row, 1)
		row += 1

		self.layout.addWidget(QtGui.QLabel(""), row, 0)
		row += 1

		self.layout.addWidget(self.savePathStatic, row, 0)
		self.layout.addWidget(self.savePathEdit, row, 1)
		row += 1

		self.layout.addWidget(self.saveFolderStatic, row, 0)
		self.layout.addWidget(self.saveFolderEdit, row, 1)
		row += 1

		self.layout.addWidget(self.fileBaseStatic, row, 0)
		self.layout.addWidget(self.fileBaseEdit, row, 1)
		row += 1

		self.layout.addWidget(self.fileNumberStatic, row, 0)
		self.layout.addWidget(self.fileNumberEdit, row, 1)
		row += 1

		self.layout.addWidget(self.saveEnableStatic, row, 0)
		self.layout.addWidget(self.saveEnableControl, row, 1)
		row += 1

		self.layout.addWidget(self.rotateImageStatic, row, 0)
		self.layout.addWidget(self.rotateImageControl, row, 1)

		row += 1
		self.layout.addWidget(self.saveNpzStatic, row, 0)
		self.layout.addWidget(self.saveNpzControl, row, 1)

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
		mintemp = max(info['temperatureRange'][0], KRBCAM_MIN_TEMP)
		maxtemp = min(info['temperatureRange'][1], KRBCAM_MAX_TEMP)

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
	data = []

	def __init__(self, Parent=None):
		super(ImageWindow, self).__init__(Parent)
		self.setFixedSize(layout_params['image'][0],layout_params['image'][1])
		self.populate()

		# Default od and count limits
		self.odLimits = [[0,3]]*KRBCAM_N_PLOT_SETTINGS
		self.countLimits = [[500,2000]]*KRBCAM_N_PLOT_SETTINGS

		# [Number of acquisitions, number of kinetics frames per acquisition]
		self.gAcqLoopLength = 0
		self.gFKSeriesLength = 0

		self.odFrames = [0]*KRBCAM_N_PLOT_SETTINGS

		# Frame select state
		self.frameSelectState = [[(None,None), (None,None), (None,None)]]*KRBCAM_N_PLOT_SETTINGS

		# Colormaps
		self.colors = KRbCustomColors()
		self.cmaps = [self.colors.whiteJet, self.colors.whiteMagma, self.colors.whitePlasma, plt.cm.jet]

		# Set default values
		self.setDefaultValues()

	def setFrameSelectState(self, fss):
		self.frameSelectState = fss

		a = self.gAcqLoopLength
		fk = self.gFKSeriesLength
		for f,w in zip(fss[0], self.frameSelectArray):
			w.setCurrentIndex(f[0]*fk + f[1])

	def getFrameSelectState(self):
		return self.frameSelectState

	def imageRotated(self, rotate):
		if rotate:
			self.colorbarOrientation = 'vertical'
		else:
			self.colorbarOrientation = 'horizontal'

	def setDefaultValues(self):
		self.minEdit.setText(str(self.odLimits[0][0]))
		self.maxEdit.setText(str(self.odLimits[0][1]))

	def resetComboBoxes(self, numKin, acqLength):
		for widget in self.frameSelectArray:
			widget.clear()
			for i in range(acqLength):
				for j in range(numKin):
					widget.addItem("{},{}".format(i, j))
			widget.setCurrentIndex(0)

	def controlComboBoxes(self, numKin, acqLength):
		if self.gAcqLoopLength != acqLength or self.gFKSeriesLength != numKin:
			self.gAcqLoopLength = acqLength
			self.gFKSeriesLength = numKin

			self.resetComboBoxes(numKin, acqLength)

	def getComboBoxState(self):
		arr = []

		for widget in self.frameSelectArray:
			text = widget.currentText()
			arr.append( (int(text.split(',')[0]), int(text.split(',')[1])) )

		return arr

	def settingChanged(self):
		setting = self.settingSelect.currentIndex()
		config = self.frameSelectState[setting]
		
		if config[0][0] == None:
			self.resetComboBoxes(self.gFKSeriesLength, self.gAcqLoopLength)
			config = self.getComboBoxState()

		for i in range(len(config)):
			(i0, i1) = config[i]
			widget = self.frameSelectArray[i]

			index = i0*self.gFKSeriesLength + i1
			widget.setCurrentIndex(index)

		self.displayData()


	# Populate GUI
	# self.displayData is a listener for any state change of the buttons
	def populate(self):
		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.toolbar = NavigationToolbar(self.canvas, self)

		self.settingLabel = QtGui.QLabel("Setting")
		self.settingSelect = QtGui.QComboBox(self)
		self.settingSelect.addItem("0")
		self.settingSelect.addItem("1")
		self.settingSelect.setToolTip("K: 0; Rb: 1")
		self.settingSelect.currentIndexChanged.connect(self.settingChanged)

		self.frameLabel = QtGui.QLabel("Frame")
		self.frameSelect = QtGui.QComboBox(self)
		self.frameSelect.addItem("OD")
		self.frameSelect.addItem("Shadow")
		self.frameSelect.addItem("Light")
		self.frameSelect.addItem("Dark")
		self.frameSelect.currentIndexChanged.connect(self.displayData)

		self.shadowFrameLabel = QtGui.QLabel("Shadow")
		self.shadowFrameSelect = QtGui.QComboBox(self)
		self.shadowFrameSelect.setToolTip("K: (0,0); Rb: (0,1)")
		self.shadowFrameSelect.currentIndexChanged.connect(self.displayData)

		self.lightFrameLabel = QtGui.QLabel("Light")
		self.lightFrameSelect = QtGui.QComboBox(self)
		self.lightFrameSelect.setToolTip("K: (1,0); Rb: (1,1)")
		self.lightFrameSelect.currentIndexChanged.connect(self.displayData)

		self.darkFrameLabel = QtGui.QLabel("Dark")
		self.darkFrameSelect = QtGui.QComboBox(self)
		self.darkFrameSelect.setToolTip("K: (2,0); Rb: (2,1)")
		self.darkFrameSelect.currentIndexChanged.connect(self.displayData)

		self.frameSelectArray = [self.shadowFrameSelect, self.lightFrameSelect, self.darkFrameSelect]

		self.colorLabel = QtGui.QLabel("Colormap", self)
		self.colorSelect = QtGui.QComboBox(self)
		self.colorSelect.addItem("White Jet")
		self.colorSelect.addItem("White Magma")
		self.colorSelect.addItem("White Plasma")
		self.colorSelect.addItem("Jet")
		self.colorSelect.currentIndexChanged.connect(self.displayData)
		
		self.minLabel = QtGui.QLabel("Min", self)
		self.minEdit = QtGui.QLineEdit(self)
		self.maxLabel = QtGui.QLabel("Max", self)
		self.maxEdit = QtGui.QLineEdit(self)

		self.maxEdit.returnPressed.connect(self.validateLimits)
		self.minEdit.returnPressed.connect(self.validateLimits)

		self.autoscaleButton = QtGui.QPushButton("Autoscale", self)
		self.autoscaleButton.clicked.connect(self.autoscale)

		self.spacer = QtGui.QSpacerItem(1,1)

		self.layout = QtGui.QGridLayout()

		self.layout.addWidget(self.toolbar,0,0,1,6)
		self.layout.addWidget(self.canvas,1,0,6,6)
		
		row = 8
		self.layout.addWidget(self.settingLabel, row, 0)
		self.layout.addWidget(self.settingSelect, row, 1)
		row += 1

		self.layout.addWidget(self.frameLabel, row, 0)
		self.layout.addWidget(self.frameSelect, row, 1)
		row += 1

		self.layout.addWidget(self.shadowFrameLabel, row, 0)
		self.layout.addWidget(self.shadowFrameSelect, row, 1)
		row += 1

		self.layout.addWidget(self.lightFrameLabel, row, 0)
		self.layout.addWidget(self.lightFrameSelect, row, 1)
		row += 1

		self.layout.addWidget(self.darkFrameLabel, row, 0)
		self.layout.addWidget(self.darkFrameSelect, row, 1)
		row += 1

		row = 8
		self.layout.addWidget(self.colorLabel,row,4)
		self.layout.addWidget(self.colorSelect,row,5)
		row += 1

		self.layout.addWidget(self.minLabel,row,4)
		self.layout.addWidget(self.minEdit,row,5)
		row += 1

		self.layout.addWidget(self.maxLabel,row,4)
		self.layout.addWidget(self.maxEdit,row,5)
		row += 1

		self.layout.addWidget(self.autoscaleButton,row,4,1,2)

		# Try to make the layout look nice
		for i in range(4):
			self.layout.setColumnStretch(i, 1)

		self.setLayout(self.layout)

	def autoscale(self):
		(setting, frame) = self.getConfig()

		if frame == 0:
			low = np.percentile(self.odFrames[setting], KRBCAM_AUTOSCALE_PERCENTILES[0])
			high = np.percentile(self.odFrames[setting], KRBCAM_AUTOSCALE_PERCENTILES[1])
		else:
			(i0, i1) = self.getComboBoxState()[frame-1]
			low = np.percentile(self.data[i0][i1], KRBCAM_AUTOSCALE_PERCENTILES[0])
			high = np.percentile(self.data[i0][i1], KRBCAM_AUTOSCALE_PERCENTILES[1])

		self.minEdit.setText(str(low))
		self.maxEdit.setText(str(high))
		self.validateLimits()

	# Display the data!
	def displayData(self):
		if self.data:
			try:
				# Take the button states and determine what image the user wants to see
				(setting, frame) = self.getConfig()
			# If this fails, it's usually because the combo boxes are not setup yet
			# This is okay, for example it happens when the setting is initially changed
			# In this case, just return nothing until things are okay
			except:
				return

			# Then try to plot the image
			try:

				# Get the correct colorbar limits
				if frame == 0:
					lims = self.odLimits[setting]
				else:
					lims = self.countLimits[setting]

				# Update the text boxes
				self.minEdit.setText(str(lims[0]))
				self.maxEdit.setText(str(lims[1]))

				if frame == 0:
					self.odFrames[setting] = self.calcOD(self.getComboBoxState())
					self.plot(self.odFrames[setting], lims[0], lims[1])
				else:
					(i0, i1) = self.getComboBoxState()[frame-1]
					self.plot(self.data[i0][i1], lims[0], lims[1])
				
			# AttributeError will occur if no data collected, since
			# then self.data is undefined
			except Exception as e:
				print(e)

	def setData(self, data, kinFrames, acqLength):
		self.controlComboBoxes(kinFrames, acqLength)
		self.data = self.processData(data)

	# Validate the entered values in the min and max boxes
	def validateLimits(self):
		# Try to cast to int
		try:
			max_entry = float(self.maxEdit.text())
			min_entry = float(self.minEdit.text())

			(setting, frame) = self.getConfig()

			if max_entry < min_entry:
				temp = min_entry
				min_entry = max_entry
				max_entry = temp

			if frame != 0:
				max_entry = int(max_entry)
				min_entry = int(min_entry)

			# Update our od limits or count limits
			if frame == 0:
				if min_entry == max_entry:
					max_entry += 0.1 # Avoid an issue with values pointing to each other
				self.odLimits[setting] = [min_entry, max_entry]

			else:
				if min_entry == max_entry:
					max_entry += 1 # Avoid an issue with values pointing to each other

				self.countLimits[setting] = [min_entry, max_entry]
				
			# Update the image shown on the screen
			self.displayData()
		except:
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Invalid entry for image display limits.")
			msgBox.setInformativeText("Please check entry (must be integer).")
			msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
			msgBox.exec_()

		
	# Determine which image to display
	def getConfig(self):
		config = self.getComboBoxState()
		setting = self.settingSelect.currentIndex()

		if self.frameSelectState[setting] != config:
			self.frameSelectState[setting] = config
			self.odFrames[setting] = self.calcOD(config)

		frame = self.frameSelect.currentIndex()	
		return (setting, frame)

	def calcOD(self, config):
		(s0, s1) = config[0]
		(l0, l1) = config[1]
		(d0, d1) = config[2]

		shadow = self.data[s0][s1]
		light = self.data[l0][l1]
		dark = self.data[d0][d1]

		with np.errstate(divide='ignore', invalid='ignore'):
			od = np.log((light-dark).astype(float)/(shadow-dark).astype(float))
			od += (light - shadow)/float(KRBCAM_C_SAT)
			od[np.isnan(od)] = 0
			od[np.isinf(od)] = 0
			od[od > KRBCAM_OD_MAX] = KRBCAM_OD_MAX

		return od

	# Separate images, get OD image
	def processData(self, data):
		out = []

		# Data comes in as an array sorted by FK index
		# with acquisition loop frames concatenated
		# 
		# We want to change the indices for convenience
		for i in range(self.gAcqLoopLength):
			arr = []

			# Loop through kinetics frames
			# and pull out the i-th acquisition loop frame
			for j in range(self.gFKSeriesLength):
				x = data[j]
				(length, width) = np.shape(x)

				length /= self.gAcqLoopLength

				arr.append(x[i*length:(i+1)*length])

			out.append(arr)

		# Now out should be a 2d array of data
		# First index is acquisition loop frame
		# Second index is FK frame
		return out

	# Plot the data
	def plot(self, data, vmin, vmax):
		# Clear plot
		self.figure.clear()

		# Plot the data
		ax = self.figure.add_subplot(111)
		color_index = self.colorSelect.currentIndex()
		im = ax.imshow(data, vmin=vmin, vmax=vmax, cmap=self.cmaps[color_index])

		# Add a horizontal colorbar
		self.figure.colorbar(im, orientation=self.colorbarOrientation)

		# Need to do the following to get the z data to show up in the toolbar
		numrows, numcols = np.shape(data)
		def format_coord(x, y):
		    col = int(x + 0.5)
		    row = int(y + 0.5)
		    if col >= 0 and col < numcols and row >= 0 and row < numrows:
		        z = data[row, col]
		        return '({:},{:}), z={:.2f}'.format(int(x),int(y),z)
		    else:
		        return 'x=%1.4f, y=%1.4f' % (x, y)
		ax.format_coord = format_coord

		# Update the plot
		self.canvas.draw()