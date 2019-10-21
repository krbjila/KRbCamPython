from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal
from twisted.internet.defer import inlineCallbacks
import twisted.internet.error

import time

import numpy as np
from copy import deepcopy

import sys
sys.path.append("./lib/")
sys.path.append("./lib/sdk2/")

# Our helper files
from gui_helpers import *
from andor_helpers import *
from andor_class import KRbiXon

import qtreactor.pyqt4reactor
qtreactor.pyqt4reactor.install()
from twisted.internet import reactor

# Main GUI Program
class MainWindow(QtGui.QWidget):
	# Dictionary for holding camera configuration
	# from GUI form input
	# gConfig = {
	# 	'expTime': 0.0,
	# 	'xOffset': 0,
	# 	'yOffset': 0,
	# 	'dx': 0,
	# 	'dy': 0,
	# 	'binning': 0,
	# 	'emEnable': 0,
	# 	'emGain': 0,
	# 	'fileNumber': 0,
	# 	'savePath': '',
	# 	'saveFiles': True
	# }

	gConfig = default_config
	# Camera parameters
	gCamInfo = {}

	# Verbose output?
	gFlagVerbose = KRBCAM_VERBOSE_FLAG

	# Only allow acquisition loop for external trigger!
	if KRBCAM_TRIGGER_MODE == 0: # Internal
		gFlagLoop = False
	else:
		gFlagLoop = KRBCAM_LOOP_ACQ

	# Counter for number of shots in OD series
	gAcqLoopCounter = 0

	# Acquire mode
	gAcqMode = KRBCAM_ACQ_MODE

	gSetTemp = KRBCAM_DEFAULT_TEMP
	gFileNameBase = KRBCAM_FILENAME_BASE

	def __init__(self, reactor):
		super(MainWindow, self).__init__(None)
		self.reactor = reactor
		self.setFixedSize(layout_params['main'][0],layout_params['main'][1])
		self.populate()
		self.initializeSDK()



	# Initialize the Andor SDK using our KRbFastKinetics() class built on the atmcd.py python wrapper
	def initializeSDK(self):
		# Get form data and set the acquire button to disabled
		self.gConfig = self.configForm.getFormData()
		self.acquireAbortStatus.acquireControl.setDisabled(True)

		# Initialize the object
		self.AndorCamera = KRbiXon()

		# Initialize the device
		(errf, errm) = self.AndorCamera.initializeSDK()
		# If an error, raise warnings, stop the camera, and close the window
		if errf:
			self.throwErrorMessage("SDK initialization error! Try to restart the GUI.", errm)
		# Otherwise, things are working!
		# Update the status window and connect signals for acquire and abort
		else:
			self.appendToStatus(errm)
			self.gCamInfo = self.AndorCamera.camInfo

			# Set up vertical shift speed control, pre amp gain, adc channel
			self.configForm.setupComboBoxes(self.gCamInfo)
			self.configForm.setDefaultValues()

			self.acquireAbortStatus.acquireControl.setDisabled(False)
			self.coolerControl.setTempRange(self.gCamInfo)
			self.connectSignals()


	# Connect PyQt button signals
	def connectSignals(self):
		# Acquire
		self.acquireAbortStatus.acquireControl.clicked.connect(lambda: self.setupAcquisition(self.gFlagVerbose))
		# Abort
		self.acquireAbortStatus.abortControl.clicked.connect(self.abortAcquisition)
		# CoolerOn
		self.coolerControl.coolerOnControl.clicked.connect(self.coolerOn)
		# CoolerOff
		self.coolerControl.coolerOffControl.clicked.connect(self.coolerOff)
		# Update the set temperature
		self.coolerControl.ccdSetTempEdit.returnPressed.connect(self.updateSetTempFromEdit)
		# Acquisition mode
		self.configForm.kineticsFramesEdit.valueChanged.connect(self.controlAcquisitionMode)
		# Freeze acquisitionmode
		self.acquireAbortStatus.acquireControl.clicked.connect(lambda: self.configForm.freezeForm(True))
		self.acquireAbortStatus.abortControl.clicked.connect(lambda: self.configForm.freezeForm(False))

	# Control the acquisition mode
	def controlAcquisitionMode(self):
		ind = self.configForm.kineticsFramesEdit.value()

		self.gAcqLoopLength = self.configForm.acqLengthEdit.value()
		self.gFKSeriesLength = ind # No fast kinetics series, just 1 image
		self.gFileNameBase = KRBCAM_FILENAME_BASE
		
		if ind == 0: # "Image"
			self.gAcqMode = KRBCAM_ACQ_MODE_SINGLE # Single scan
		else: # "Fast kinetics"
			self.gAcqMode = KRBCAM_ACQ_MODE_FK # Fast Kinetics

		# Update the gCamInfo struct
		# VSS may change going from FK to Image modes
		self.AndorCamera.updateVerticalShiftSpeeds(self.gAcqMode)
		self.gCamInfo = self.AndorCamera.camInfo

		self.configForm.vssControl.clear()
		# Populate vertical shift speeds
		for val in self.gCamInfo['vss']:
			self.configForm.vssControl.addItem("{:.2} usec".format(val))
		self.configForm.vssControl.setCurrentIndex(default_config['vss'])


	# Turn on cooler
	def coolerOn(self):
		# Get desired set temp from form
		# Update SetTemperature via SDK
		self.updateSetTemp()

		# Turn on cooler
		ret = self.AndorCamera.CoolerON()
		if ret != self.AndorCamera.DRV_SUCCESS:
			self.throwErrorMessage("CoolerON error!", "Error code: {}".format(ret))
			return -2

		# Status log
		self.coolerControl.coolerStatusEdit.setText("Cooler started...")

		# Set a timer for checking the temperature
		self.tempCallback = self.reactor.callLater(KRBCAM_TEMP_TIMER, self.checkTempLoop)

	# This fires when the user hits return in the Set Temperature line edit
	# It checks if the input is valid, throws a message box if it's not
	# If the input is valid, it confirms via a message box that
	# the user actually wants to change the set temperature
	def updateSetTempFromEdit(self):
		# Get the form input
		msg = self.coolerControl.ccdSetTempEdit.text()

		# Try to cast the set temperature to an int
		# If it's not valid input, then it will throw a ValueError
		try:
			temp = int(msg)

			# Confirm with user
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Set temperature changed.")
			msgBox.setInformativeText("Do you want to change the set temperature to " + msg + " degrees C?")
			msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
			msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
			ret = msgBox.exec_()

			# If user confirms, update the set temperature
			# Temp bounds are checked in updateSetTemp()
			if ret == QtGui.QMessageBox.Ok:
				self.updateSetTemp()
		# Not valid input
		except ValueError:
			# Warn user, but do nothing
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Set temperature changed.")
			msgBox.setInformativeText("Invalid set temperature: \"" + msg + "\". Enter an integer.")
			msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
			msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
			ret = msgBox.exec_()

	# Get form input and update the SetTemperature
	def updateSetTemp(self):
		# Try to get the set temperature from the text input
		try:
			setTemp = int(self.coolerControl.ccdSetTempEdit.text())
		# if some error, just put our default temp defined in andor_helpers.py
		except:
			setTemp = self.gSetTemp

		# Take the more conservative of the camera limits and our hard limits
		# defined in andor_helpers.py
		minTemp = max(self.gCamInfo['temperatureRange'][0], KRBCAM_MIN_TEMP)
		maxTemp = min(self.gCamInfo['temperatureRange'][1], KRBCAM_MAX_TEMP)

		# Make sure the setTemp is within the bounds
		if setTemp < minTemp:
			setTemp = minTemp
		elif setTemp > maxTemp:
			setTemp = maxTemp

		# Update text edit with the actual set temp
		self.coolerControl.ccdSetTempEdit.setText(str(setTemp))

		# Try to set the temperature
		ret = self.AndorCamera.SetTemperature(setTemp)
		if ret != self.AndorCamera.DRV_SUCCESS:
			self.throwErrorMessage("SetTemperature error!", "Error code: {}".format(ret))
			return -1
		
		# Update status log
		self.appendToStatus("Set temperature is {} C.\n".format(setTemp))

		# Store current set temp
		self.gSetTemp = setTemp


	# Query the camera for its current temperature
	# Returns (errorFlag, temperature)
	# errorFlag = -1 if an error occured
	# temperature is the camera temp in degrees C (0 if an error occurred)
	def checkTemp(self):
		# Ask camera for its temperature
		(ret, temp) = self.AndorCamera.GetTemperature()

		# Throw message box if error
		if ret == self.AndorCamera.DRV_NOT_INITIALIZED or ret == self.AndorCamera.DRV_ERROR_ACK:
			self.throwErrorMessage("GetTemperature error!", "Error code: {}".format(ret))
			return (-1, 0)
		# Otherwise, current the current temp field
		else:
			self.coolerControl.ccdCurrentTempEdit.setText(str(temp))

			# Update the cooler status field
			if ret == self.AndorCamera.DRV_TEMP_OFF:
				self.coolerControl.coolerStatusEdit.setText("Cooler off.")
			elif ret == self.AndorCamera.DRV_TEMP_STABILIZED:
				self.coolerControl.coolerStatusEdit.setText("Temp. stabilized.")
			elif ret == self.AndorCamera.DRV_TEMP_NOT_REACHED:
				self.coolerControl.coolerStatusEdit.setText("Temp. not reached.")
			elif ret == self.AndorCamera.DRV_TEMP_DRIFT:
				self.coolerControl.coolerStatusEdit.setText("Temp. has drifted.")
			elif ret == self.AndorCamera.DRV_TEMP_NOT_STABILIZED:
				self.coolerControl.coolerStatusEdit.setText("Temp. reached but not stabilized.")

			return (0, temp)

	# The loop that controls temperature checking
	# Implemented using twisted's reactor.callLater method
	def checkTempLoop(self):
		# Check the temeprature
		(err, temp) = self.checkTemp()

		# checkTemp returns -1 if error -- in that case, stop the loop
		# Otherwise, keep looping
		if err != -1:
			self.tempCallback = self.reactor.callLater(KRBCAM_TEMP_TIMER, self.checkTempLoop)

	# Turn off the cooler
	def coolerOff(self):
		errf = 0

		# Turn off the cooler
		ret = self.AndorCamera.CoolerOFF()
		if ret != self.AndorCamera.DRV_SUCCESS:
			self.throwErrorMessage("CoolerOFF error!", "Error code: {}".format(ret))
			errf = 1

		# Update status log
		if errf:
			self.appendToStatus("There was an error stopping the cooler.\n")
			return -1
		else:
			self.appendToStatus("Cooler stopped.\n")
			return 0
		
	# Setup acquisition
	def setupAcquisition(self, flagVerbose=True):
		# armiXon sets the basic acquisition details
		# e.g., acquisition mode, read mode, shutter mode, trigger mode, em gain mode
		(errf, errm) = self.AndorCamera.armiXon()

		# Check for errors
		if errf:
			self.throwErrorMessage("KRbFastKinetics.armiXon error!", errm)
			return -1
		else:
			if flagVerbose:
				self.appendToStatus(errm)
			self.gCamInfo = self.AndorCamera.camInfo

		# armiXon gets some information from the hardware
		# At this point we have all the information we need to validate the
		# user's desired camera configuration
		# Validate and update the form with the correct values
		self.gConfig = self.validateFormInput(self.configForm.getFormData())
		self.configForm.setFormData(self.gConfig)

		if self.gConfig['kinFrames'] == 1:
			self.gAcqMode = KRBCAM_ACQ_MODE_SINGLE
		else:
			self.gAcqMode = KRBCAM_ACQ_MODE_FK
		self.gFKSeriesLength = self.gConfig['kinFrames']
		self.gAcqLoopLength = self.gConfig['acqLength']


		# setupAcquisition sets the EM settings, ad channel, shift speeds, pre amp settings
		(errf, errm) = self.AndorCamera.setupAcquisition(self.gConfig)

		if errf:
			self.throwErrorMessage("KRbiXon.setupAcquisition error!", errm)
			return -2
		elif flagVerbose:
			self.appendToStatus(errm)

		if self.gAcqMode == KRBCAM_ACQ_MODE_FK:
			# setupAcquisition sets the EM settings, ad channel, shift speeds, pre amp settings
			(errf, errm) = self.AndorCamera.setupFastKinetics(self.gConfig)

			if errf:
				self.throwErrorMessage("KRbiXon.setupFastKinetics error!", errm)
				return -2
			elif flagVerbose:
				self.appendToStatus(errm)
		elif self.gAcqMode == KRBCAM_ACQ_MODE_SINGLE:
			# setupAcquisition sets the EM settings, ad channel, shift speeds, pre amp settings
			(errf, errm) = self.AndorCamera.setupImage(self.gConfig)

			if errf:
				self.throwErrorMessage("KRbiXon.setupImage error!", errm)
				return -2
			elif flagVerbose:
				self.appendToStatus(errm)

		# Enable abort button, disable acquire button
		self.acquireAbortStatus.acquire()

		# Reset OD series counter
		self.gAcqLoopCounter = 0

		# Start acquiring data!
		# dataArray is passed between startAcquisition and checkForData methods
		# to hold data
		# Hopefully this does not result in memory leaks...?
		dataArray = []
		self.startAcquisition(dataArray)

	# Start acquisition
	# Tells the camera to start acquiring data
	# Also sets up a deferred call to the checkForData method
	def startAcquisition(self, data):
		# Start acquiring
		ret = self.AndorCamera.StartAcquisition()
		msg = self.AndorCamera.handleErrors(ret, "StartAcquisition error: ", "Acquiring...")

		if ret != self.AndorCamera.DRV_SUCCESS:
			self.throwErrorMessage("Acquisition error!", msg)
		else:
			# Set a timer for looking for the data
			self.appendToStatus("Acquiring...\n")
			self.acquireCallback = self.reactor.callLater(KRBCAM_ACQ_TIMER, self.checkForData, data)

	# Method that fires after the KRBCAM_ACQ_TIMER time has elapsed
	# data argument holds list of numpy arrays that contain the data collected so far in this acquisition
	def checkForData(self, data):
		# Check if the camera is still acquiring:
		(ret, status) = self.AndorCamera.GetStatus()
		msg = self.AndorCamera.handleErrors(ret, "GetStatus error: ", "")

		# if error, throw message, quit SDK
		if ret != self.AndorCamera.DRV_SUCCESS:
			self.throwErrorMessage("Error communicating with camera.", msg)
		else:
			# If still acquiring, run the timer again
			if status == self.AndorCamera.DRV_ACQUIRING:
				# Check back for new data later
				self.acquireCallback = self.reactor.callLater(KRBCAM_ACQ_TIMER, self.checkForData, data)

			# If idle, then data has been acquired
			elif status == self.AndorCamera.DRV_IDLE:
				# Increment OD series counter since we've taken an image
				self.gAcqLoopCounter += 1

				# Update status log
				self.appendToStatus("Acquired {} of {} in series.\n".format(self.gAcqLoopCounter, self.gAcqLoopLength))
				
				# Get the data off of the camera
				newData = self.getData()

				# Append it to the data array
				if self.gAcqLoopCounter > 1:
					for i in range(len(data)):
						data[i] = np.concatenate((data[i], newData[i]))
				else:
					for i in range(len(newData)):
						data.append(np.array(newData[i]))

				# If need to take more in the OD series, acquire again
				if self.gAcqLoopCounter < self.gAcqLoopLength:
					self.startAcquisition(data)
				# Otherwise we are done acquiring!
				else:
					# Double check the directory
					# This catches when the directory should roll over at midnight
					self.configForm.checkDir()
					self.gConfig = self.configForm.getFormData()

					# If we're saving the files
					if self.gConfig['saveFiles']:
	 					# Save data
	 					if self.gAcqMode == KRBCAM_ACQ_MODE_FK:

	 						# This is an ugly way of doing this but oh well
	 						savearray = data[0]
	 						# Save all the data as one file
	 						# So the data file will have e.g.
	 						# K shadow, light, dark, Rb shadow, light, dark
							for j in range(1, self.gFKSeriesLength):
								savearray = np.concatenate((savearray, data[j]))
							self.saveData(savearray)
							self.appendToStatus("Data saved.\n")
						elif self.gAcqMode == KRBCAM_ACQ_MODE_SINGLE:
							self.saveData(data[0])
							self.appendToStatus("Data saved.\n")
					else:
						self.appendToStatus("Data saving is turned off.\n")

						# Update file number
						self.gConfig['fileNumber'] += 1
						self.configForm.setFormData(self.gConfig)

					# Display the data
					self.imageWindow.setData(data, self.gFKSeriesLength, self.gAcqLoopLength)
					self.imageWindow.displayData()
	
					# if not looping:
					if not self.gFlagLoop:
						# Disable abort button, enable acquire button
						self.acquireAbortStatus.abort()
					# if looping:
					else:
						self.setupAcquisition(False)

			# Otherwise some error has occurred in the acquisition
			else:
				self.throwErrorMessage("Error in acquisition loop.", "Camera state is {}".format(status))

	# Get data from camera
	def getData(self):
		# First need to get the total size of the image in binned pixels
		dy = self.gConfig['dy']
		dx = self.gConfig['dx']

		if (self.gConfig['binning']):
			dy /= KRBCAM_BIN_SIZE
			dx /= KRBCAM_BIN_SIZE
		dataLength = self.gFKSeriesLength * dy * dx

		# Now ask the camera for data
		# getData first queries the camera for available images
		# then takes the images
		(errf, errm, data) = self.AndorCamera.getData(dataLength)
		if errf:
			self.throwErrorMessage("Data readout error:", errm)
			self.abortAcquisition()
			return -1
		else:
			# Data is returned as a ctypes array of c_longs
			# Need to convert to numpy array
			data = np.ctypeslib.as_array(data)

			out = []

			# Data is returned as one long array
			# Need to split it up to get the individual images
			num_images = self.gFKSeriesLength
			image_length = len(data)/num_images
			
			# For each Fast Kinetics frame:
			for i in range(num_images):
				# Get the image and resize to the correct dimensions
				image = np.resize(data[i*image_length : (i+1)*image_length], (dy, dx))
				out.append(image)

			return out

	# Save data array
	def saveData(self, data_array):
		# The save path
		path = self.gConfig['savePath'] + self.gFileNameBase + str(self.gConfig['fileNumber'])
		# Define a temporary path to avoid conflicts when writing file
		# Otherwise, fitting program autoloads the file before writing is complete
		path_temp = path + "_temp"
		path += ".csv"
		path_temp += ".csv"

		# Open the file and write the data,
		# comma-delimited
		dy, dx = np.shape(data_array)
		with open(path_temp, 'w') as f:
			for j in range(dy):
				for k in range(dx):
					f.write(str(data_array[j][k]))
					if k < dx - 1:
						f.write(',')
				f.write('\n')
		# Once file is written, rename to the correct filename
		os.rename(path_temp, path)

	# Abort an acquisition
	def abortAcquisition(self):
		# First, stop camera acquisition
		ret = self.AndorCamera.AbortAcquisition()
		if ret == self.AndorCamera.DRV_SUCCESS:
			self.appendToStatus("Camera acquisition aborted successfully.\n")
		elif ret != self.AndorCamera.DRV_IDLE:
			self.throwErrorMessage("AbortAcquisition error!", "Error code: {}".format(ret))

		# Next, close the internal shutter for safety
		ret2 = self.AndorCamera.SetShutter(1, 2, 0, 0)
		if ret2 == self.AndorCamera.DRV_SUCCESS:
			self.appendToStatus("Internal shutter closed.\n")
		else:
			self.throwErrorMessage("SetShutter error!", "Error code: {}".format(ret2))

		# Next, kill the getData callback
		try:
			self.acquireCallback.cancel()
		# This happens if abort button is hit before ever acquiring
		except AttributeError:
			self.throwErrorMessage("Abort: ", "Acquisition loop not started.")
		# This happens if we try to abort when the acquisition is already over, or not started
		except twisted.internet.error.AlreadyCalled:
			self.throwErrorMessage("Abort: ", "Acquisition loop already completed.")

		# Enable acquire, disable abort buttons
		self.acquireAbortStatus.abort()

	# Populate the gui
	def populate(self):
		self.setWindowTitle('KRbCam: iXon Fast Kinetics Imaging')

		self.layout = QtGui.QGridLayout()

		self.configForm = ConfigForm(self)
		self.layout.addWidget(self.configForm, 0, 0)

		self.acquireAbortStatus = AcquireAbortStatus(self)
		self.layout.addWidget(self.acquireAbortStatus, 1, 0)

		self.coolerControl = CoolerControl(self)
		self.layout.addWidget(self.coolerControl, 2, 0)

		self.imageWindow = ImageWindow(self)
		self.layout.addWidget(self.imageWindow, 0, 1)
		
		self.setLayout(self.layout)

	# Validate the configuration form input vs the camera data
	def validateFormInput(self, form):
		fk = form['kinFrames']

		# validate against camera info
		x_limit = self.gCamInfo['detDim'][0]
		y_limit = self.gCamInfo['detDim'][1]

		# If in Fast kinetics mode,
		# the number of rows should be either the number of exposed rows
		# or at most the size of the device / number of shots in FK series
		if self.gAcqMode == KRBCAM_ACQ_MODE_FK:
			if KRBCAM_EXPOSED_ROWS < self.gCamInfo['detDim'][1] / fk:
				y_limit = KRBCAM_EXPOSED_ROWS
			else:
				y_limit = self.gCamInfo['detDim'][1] / fk

		# Keep the x/y offsets within the bounds of the CCD array
		if form['xOffset'] > x_limit:
			form['xOffset'] = x_limit - 1
		if form['yOffset'] > y_limit:
			form['yOffset'] = y_limit - 1

		# Make sure the ROI fits in the CCD array
		dx_limit = x_limit - form['xOffset']
		if form['dx'] > dx_limit:
			form['dx'] = dx_limit
		dy_limit = y_limit - form['yOffset']
		if form['dy'] > dy_limit:
			form['dy'] = dy_limit

		# If binning, make sure ROI dimensions are
		# multiples of the bin size
		if form['binning']:
			form['dy'] -= form['dy'] % KRBCAM_BIN_SIZE
			form['dx'] -= form['dx'] % KRBCAM_BIN_SIZE

		# Check em range
		if form['emEnable']:
			if form['emGain'] > self.gCamInfo['emGainRange'][1]:
				form['emGain'] = self.gCamInfo['emGainRange'][1]
			if form['emGain'] < self.gCamInfo['emGainRange'][0]:
				form['emGain'] = self.gCamInfo['emGainRange'][0]
		else:
			form['emGain'] = 0

		# If in Fast Kinetics mode, the width of the image should be
		# the entire width of the CCD arrray
		if self.gAcqMode == 4:
			form['dx'] = self.gCamInfo['detDim'][0]

		return form

	def throwErrorMessage(self, header, msg):
		messageBox = QtGui.QMessageBox()
		messageBox.setText(header)
		messageBox.setInformativeText(msg)
		messageBox.exec_()

	def appendToStatus(self, msg):
		self.acquireAbortStatus.statusEdit.append(msg)
		self.acquireAbortStatus.statusEdit.moveCursor(QtGui.QTextCursor.End)
		self.acquireAbortStatus.statusEdit.ensureCursorVisible()

	# This function is automatically called by PyQt when the GUI is closed
	# We need to check here that the temperature is safe!
	# If the camera is still cold (<-20 deg C) then the camera may be damaged
	# by changing temperature too fast
	#
	# The window will close when the function returns if we run the method event.accept()
	# If we run event.ignore(), the window does not close and program keeps running
	def closeEvent(self, event):
		flag = False

		# Try to stop the acquisition loop
		try:
			self.acquireCallback.cancel()
		except:
			pass
		# Next, kill the checkTemp callback
		try:
			self.tempCallback.cancel()
		except:
			pass

		# Try to get the temperature
		(err, temp) = self.checkTemp()

		# If an error getting the temperature, notify the user
		if err == -1:
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Error getting CCD temperature.")
			msgBox.setInformativeText("Do you want to force the SDK to close?")
			msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
			msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
			ret = msgBox.exec_()

			# Force quit if user says yes
			if ret == QtGui.QMessageBox.Ok:
				flag = True

		# Otherwise, we got the temperature correctly
		else:
			# Check that the temperature is still colder than the safe temperature for shut down
			# For iXon, this is -20 degrees C
			# The manual says that shutting down the SDK when the camera is colder than this
			# can lead to damage
			#
			# If the temperature is too cold, warn the user
			# Do not give them the option to shut down! If the program has made it to this point,
			# the cooler has correctly shut off and the GetTemperature function is working
			# so all the user has to do is wait for the camera to warm up to a safe temperature
			if temp < KRBCAM_SAFE_TEMP: # -20 for iXon
				msgBox = QtGui.QMessageBox()
				msgBox.setText("CCD temperature is too low.")
				msgBox.setInformativeText("Current temp is {}, safe temp is >{}.\nThe camera should be warming up.".format(temp, KRBCAM_SAFE_TEMP))
				msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
				ret = msgBox.exec_()

			# Otherwise, the camera should be safe to turn off
			# But still warn the user as a double check
			else:
				msgBox = QtGui.QMessageBox()
				msgBox.setText("CCD temperature is safe for shut down.")
				msgBox.setInformativeText("Current temp is {}, safe temp is >{}.\nDo you want to stop the SDK?".format(temp, KRBCAM_SAFE_TEMP))
				msgBox.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
				msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
				ret = msgBox.exec_()

				# On ok, kill program
				if ret == QtGui.QMessageBox.Ok:
					flag = True

		if flag:
			self.coolerOff()
			self.tryToCloseNicely()
			event.accept()
		else:
			self.tempCallback = self.reactor.callLater(KRBCAM_TEMP_TIMER, self.checkTempLoop)
			event.ignore()

	# Last actions
	def tryToCloseNicely(self):
		try:
			del(self.AndorCamera)
		except: pass

		# Try to end the acquisition loop
		try:
			self.acquireCallback.cancel()
		except: pass
		
		# Try to end the temperature checking loop
		try:
			self.tempCallback.cancel()
		except: pass

		# Try to stop the twisted reactor
		try:
			self.reactor.stop()
		except Exception as e:
			print e


if __name__ == '__main__':
    a = QtGui.QApplication([])
    a.setQuitOnLastWindowClosed(True)
    widget = MainWindow(reactor)

    appico = QtGui.QIcon()
    appico.addFile('main.ico')
    widget.setWindowIcon(appico)

    widget.show()
    reactor.runReturn()
    sys.exit(a.exec_())
