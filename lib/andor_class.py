import sys
import numpy as np
import PyQt4

sys.path.append('./sdk2/')
import atmcd

from andor_helpers import *

# Base class for Andor Camera
class KRbiXon(atmcd.atmcd):
	# Caps struct defined in atmcd.py
	caps = atmcd.AndorCapabilities()

	# camInfo dict same keys as the dict in the main GUI program
	camInfo = {
		'model': "", # Head model number
		'detDim' : [0, 0], # {x, y} dimensions in pixels
		'internalShutter': 0, # Has internal shutter?
		'shutterMinT': [0, 0], # {closing time, opening time}
		'emGainRange': [0, 0], # {emLow, emHigh}
		'temperatureRange': [20, 20] # {mintemp, maxtemp}
	}
	errorFlag = 0

	def __init__(self):
		super(KRbiXon, self).__init__()

	# Try to stop acquisition, etc. before exiting the SDK
	# Ensure that SDK is shut down before the program ends
	def __del__(self):
		try:
			self.exitGracefully()
		except:
			pass

	# Ensure that SDK is shut down before the program ends
	def exitGracefully(self):
		msg = ""

		try:
			# Check status
			status = self.GetStatus()
			if status == self.DRV_ACQUIRING:
				# If acquiring, abort
				ret = self.AbortAcquisition()
				msg += self.handleErrors(ret, "AbortAcquisition error: ", "Aborted successfully.\n")
		except:
			pass

		try:
			# Ensure that internal shutter is closed for safety!
			ret = self.SetShutter(1, 2, 0, 0)
			msg += self.handleErrors(ret, "SetShutter error: ", "Shutter closed.\n")
		except:
			pass

		# Shut down the SDK
		ret = self.ShutDown()
		msg += self.handleErrors(ret, "ShutDown error: ", "SDK shut down successfully.\n")

		print msg

	# Initialize SDK, check camera capabilities, get basic info (stored in camInfo)
	# Set fan mode for cooler
	def initializeSDK(self):
		self.errorFlag = 0
		msg = ""

		# Initialize
		ret = self.Initialize("/usr/local/etc/andor") #initialise camera
		msg += self.handleErrors(ret, "Init. error: ", "SDK initialized.\n")

		# Get capabilities structure
		(ret, self.caps) = self.GetCapabilities()
		msg += self.handleErrors(ret, "GetCapabilities error: ", "")
		
		# Get head model
		(ret, self.camInfo['model']) = self.GetHeadModel()
		successMsg = "Head model is " + str(self.camInfo['model']) + ".\n"
		msg += self.handleErrors(ret, "GetHeadModel error: ", successMsg)
		
		# Get detector dimensions
		(ret, dim0, dim1) = self.GetDetector()
		self.camInfo['detDim'][0] = dim0
		self.camInfo['detDim'][1] = dim1
		successMsg = "Array is " + str(dim0) + " x " + str(dim1) + " pixels.\n"
		msg += self.handleErrors(ret, "GetDetector error: ", successMsg)
		
		# Get internal shutter specs
		(ret, self.camInfo['internalShutter']) = self.IsInternalMechanicalShutter()
		if (self.camInfo['internalShutter']):
			successMsg = "Has internal shutter.\n"
		else:
			successMsg = "No internal shutter.\n"
		msg += self.handleErrors(ret, "IsInternalMechanicalShutter error: ", successMsg)
		
		# Get internal shutter specs
		(ret, minT, maxT) = self.GetShutterMinTimes()
		self.camInfo['shutterMinT'][0] = minT
		self.camInfo['shutterMinT'][1] = maxT
		successMsg = "Minimum shutter closing (opening) time (ms): " + str(minT) + " (" + str(maxT) + ").\n"
		msg += self.handleErrors(ret, "GetShutterMinTimes error: ", successMsg)

		# Get allowed temperature range
		(ret, mintemp, maxtemp) = self.GetTemperatureRange()
		self.camInfo['temperatureRange'][0] = mintemp
		self.camInfo['temperatureRange'][1] = maxtemp
		successMsg = "Allowed temperature range is {} to {} degrees celsius.\n".format(mintemp, maxtemp)
		msg += self.handleErrors(ret, "GetTemperatureRange error: ", successMsg)

		# Set fan mode for cooling
		ret = self.SetFanMode(KRBCAM_FAN_MODE)
		if KRBCAM_FAN_MODE == 0:
			successMsg = "Fan set to full.\n"
		elif KRBCAM_FAN_MODE == 1:
			successMsg = "Fan set to low.\n"
		elif KRBCAM_FAN_MODE == 2:
			successMsg = "Fan turned off.\n"
		msg += self.handleErrors(ret, "SetFanMode error: ", successMsg)

		# Return (errorFlag, msg)
		# If error, then errorFlag = 1, and msg will contain the error message
		# If no error, then errorFlag = 0, and msg contains the success messages
		return (self.errorFlag, msg)

	# For convenience in error checking
	def handleErrors(self, errorCode, msg = "", successMsg = ""):
		if errorCode == self.DRV_SUCCESS:
			return successMsg
		elif errorCode == self.DRV_VXDNOTINSTALLED:
			msg += "VxD not installed\n"
		elif errorCode == self.DRV_INIERROR:
			msg += "Unable to load \"DETECTOR.INI\"\n"
		elif errorCode == self.DRV_COFERROR:
			msg += "Unable to load \"*.COF\"\n"
		elif errorCode == self.DRV_FLEXERROR:
			msg += "Unable to load \"*.RBF\"\n"
		elif errorCode == self.DRV_ERROR_FILELOAD:
			msg += "Unable to load \"*.COF\" or \"*.RBF\" files\n"
		elif errorCode == self.DRV_ERROR_PAGELOCK:
			msg += "Unable to acquire lock on requested memory\n"
		elif errorCode == self.DRV_USBERROR:
			msg += "Unable to detect USB device or not USB2.0\n"
		elif errorCode == self.DRV_ERROR_NOCAMERA:
			msg += "No camera found\n"
		elif errorCode == self.DRV_P1INVALID:
			msg += "Parameter 1 invalid\n"
		elif errorCode == self.DRV_P2INVALID:
			msg += "Parameter 2 invalid\n"
		elif errorCode == self.DRV_P3INVALID:
			msg += "Parameter 3 invalid\n"
		elif errorCode == self.DRV_P4INVALID:
			msg += "Parameter 4 invalid\n"
		elif errorCode == self.DRV_P5INVALID:
			msg += "Parameter 5 invalid\n"
		elif errorCode == self.DRV_P6INVALID:
			msg += "Parameter 6 invalid\n"
		elif errorCode == self.DRV_P7INVALID:
			msg += "Parameter 7 invalid\n"
		else:
			msg += "Error code: {}\n".format(errorCode);

		errorFlag = 1
		return msg

# More specialized class for setting up Fast Kinetics acquisitions
class KRbFastKinetics(KRbiXon):
	def __init__(self):
		super(KRbFastKinetics, self).__init__()

	# Setup acquisition modes, get allowed EM gain range
	def armiXon(self):
		self.errorFlag = 0
		msg = ""

		ret = self.SetAcquisitionMode(KRBCAM_ACQ_MODE)
		successMsg = "Acquisition mode set to " + acq_modes[str(KRBCAM_ACQ_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetAcquisitionMode error: ", successMsg)

		ret = self.SetReadMode(KRBCAM_READ_MODE)
		successMsg = "Read mode set to " + read_modes[str(KRBCAM_READ_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetReadMode error: ", successMsg)

		ret = self.SetShutter(1, KRBCAM_USE_INTERNAL_SHUTTER, self.camInfo['shutterMinT'][0], self.camInfo['shutterMinT'][1])
		successMsg = "Shutter mode set to " + shutter_modes[str(KRBCAM_USE_INTERNAL_SHUTTER)] + ".\n"
		msg += self.handleErrors(ret, "SetShutter error: ", successMsg)

		ret = self.SetTriggerMode(KRBCAM_TRIGGER_MODE)
		successMsg = "Trigger mode set to " + trigger_modes[str(KRBCAM_TRIGGER_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetTriggerMode error: ", successMsg)

		ret = self.SetEMGainMode(KRBCAM_EM_MODE)
		successMsg = "EM mode set to " + em_modes[str(KRBCAM_EM_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetEMGainMode error: ", successMsg)

		(ret, range0, range1) = self.GetEMGainRange()
		self.camInfo['emGainRange'][0] = range0
		self.camInfo['emGainRange'][1] = range1

		return (self.errorFlag, msg)

	# Set EM gain, exposure times, and readout times
	# Get acquisition timings
	def setupAcquisition(self, config):
		self.errorFlag = 0
		msg = ""

		ret = self.SetEMCCDGain(config['emGain'])
		successMsg = "EM Gain set to " + str(config['emGain']) + ".\n"
		msg += self.handleErrors(ret, "SetEMCCDGain error: ", successMsg)

		exposure = config['expTime'] * 1e-3
		if config['binning']:
			binning = KRBCAM_BIN_SIZE
		else:
			binning = 1
		ret = self.SetFastKineticsEx(config['dy'], KRBCAM_FK_SERIES_LENGTH, exposure, 4, binning, binning, config['yOffset'])
		msg += self.handleErrors(ret, "SetFastKineticsEx error: ", "Fast Kinetics set.\n")

		(ret, realExp) = self.GetFKExposureTime()
		successMsg = "Real FK exposure time is {:.3} ms.\n".format(realExp * 1e3)
		msg += self.handleErrors(ret, "GetFKExposureTime error: ", successMsg)

		(ret, realExp, realAcc, realKin) = self.GetAcquisitionTimings()
		successMsg = "Real (exp., acc., kin.) times are ({:.3}, {:.3}, {:.3}) ms.\n".format(realExp * 1e3, realAcc * 1e3, realKin * 1e3)
		msg += self.handleErrors(ret, "GetAcquisitionTimings error: ", successMsg)

		(ret, readout) = self.GetReadOutTime()
		successMsg = "Readout time is {:.3} ms.\n".format(readout * 1e3)
		msg += self.handleErrors(ret, "GetReadoutTime error: ", successMsg)

		return (self.errorFlag, msg)

	# Get data from camera
	def getData(self, dataLength):
		self.errorFlag = 0
		msg = ""

		# Query camera for the number of available images
		# For our typical use, should be the number of images in the kinetic series
		# e.g., for imaging K and Rb one shot each it should be 2
		(ret, first, last) = self.GetNumberAvailableImages()
		successMsg = "Available images are {} to {}.\n".format(first, last)
		msg += self.handleErrors(ret, "GetNumberAvailableImages error: ", successMsg)

		# Read the images off of the camera
		# Note that "data" is a ctypes array of longs
		# This needs to be converted later into something python can use
		(ret, data, validfirst, validlast) = self.GetImages(first, last, dataLength)
		msg += self.handleErrors(ret, "GetImages error: ", "Readout complete!\n")

		return (self.errorFlag, msg, data)
