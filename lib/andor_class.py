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
		'temperatureRange': [20, 20], # {mintemp, maxtemp}
		'vss': [], # Vertical shift speeds
		'hss': [], # Horizontal shift speeds
		'hssPreAmp': [], # Pre amp gain availability
		'preAmpGain': [], # Pre amp gain values
		'adChannels': 0 # Number of ADC channels
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
			(ret, status) = self.GetStatus()
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

		# Get available cameras
		(ret, nCameras) = self.GetAvailableCameras()
		successMsg = str(nCameras) + " are available.\n"
		msg += self.handleErrors(ret, "GetAvailableCameras error: ", successMsg)

		serials = []
		for i in range(nCameras):
			self.selectCamera(i)
			(errf, ser, errm) = self.getCameraSerial(True)

			if not errf:
				serials.append(ser)

		return (self.errorFlag, serials, msg)

	def initializeCamera(self):
		ret = self.Initialize("/usr/local/etc/andor") #initialise camera
		msg = self.handleErrors(ret, "Init. error: ", "SDK initialized.\n")
		return (self.errorFlag, msg)

	# Select camera by index
	def selectCamera(self, index):
		msg = ""

		(ret, handle) = self.GetCameraHandle(index)
		msg += self.handleErrors(ret, "GetCameraHandle error: ", "")

		# Switch to camera
		ret = self.SetCurrentCamera(handle)
		successMsg = "Current camera set to " + str(index) + ".\n"
		msg += self.handleErrors(ret, "SetCurrentCamera error: ", successMsg)

		return (self.errorFlag, msg)

	# Get the serial number of the selected camera
	# Need to run self.selectCamera(index) first
	def getCameraSerial(self, shutdown=False):
		msg = ""

		# Need to initialize camera first
		(errf, errm) = self.initializeCamera()

		if not errf:
			# Get serial number
			(ret, serial) = self.GetCameraSerialNumber()
			successMsg = "Serial number is " + str(serial) + ".\n"
			msg += self.handleErrors(ret, "GetCameraSerialNumber error: ", successMsg)

			if shutdown:
				# De-initialize selected camera
				ret = self.ShutDown()
				msg += self.handleErrors(ret, "ShutDown error: ", "SDK shut down successfully.\n")

			return (self.errorFlag, serial, msg)
		else:
			return (self.errorFlag, -1, msg)

	def setupCamera(self):
		msg = ""

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

		# Get vertical shift speeds
		(err, err_msg) = self.updateVerticalShiftSpeeds(KRBCAM_ACQ_MODE)
		msg += err_msg

		(ret, nad) = self.GetNumberADChannels()
		successMsg = "Number of A/D channels is " + str(nad) + ".\n"
		msg += self.handleErrors(ret, "GetNumberADChannels error: ", successMsg)
		self.camInfo['adChannels'] = nad

		(ret, npreamp) = self.GetNumberPreAmpGains()
		successMsg = "Number of preamp gains is " + str(npreamp) + ".\n"
		msg += self.handleErrors(ret, "GetNumberPreAmpGains error: ", successMsg)
		for j in range(npreamp):
			(ret, gain) = self.GetPreAmpGain(j)
			successMsg = "Preamp gain " + str(j) + " is {:.3}.\n".format(gain)
			msg += self.handleErrors(ret, "GetPreAmpGain error: ", successMsg)
			self.camInfo['preAmpGain'].append(gain)

		hss_top_amp = []
		hss_top_val = []
		for i in range(self.camInfo['adChannels']):
			typ_amp = []
			typ_val = []
			for j in range(2):
				(ret, numhss) = self.GetNumberHSSpeeds(i,j)
				successMsg = "Number of HS speeds ({}, {}): {}.\n".format(i,j,numhss)
				msg += self.handleErrors(ret, "GetNumberHSSpeeds error: ", successMsg)

				hss_amp = []
				hss_val = []
				for k in range(numhss):
					(ret, speed) = self.GetHSSpeed(i,j,k)
					successMsg = "({},{},{}) speed: {:.1f} MHz.\n".format(i,j,k,speed)
					msg += self.handleErrors(ret, "GetHSSpeed error: ", successMsg)

					hss_val.append(speed)

					preamp = []
					for m in range(len(self.camInfo['preAmpGain'])):
						(ret, available) = self.IsPreAmpGainAvailable(i,j,k,m)
						successMsg = "({},{},{},{}): {}\n".format(i,j,k,m,available)
						msg += self.handleErrors(ret, "IsPreAmpGainAvailble error: ", successMsg)
						preamp.append(available)
					hss_amp.append(preamp)

				typ_amp.append(hss_amp)
				typ_val.append(hss_val)
			hss_top_amp.append(typ_amp)
			hss_top_val.append(typ_val)
		self.camInfo['hss'] = hss_top_val
		self.camInfo['hssPreAmp'] = hss_top_amp


		# Return (errorFlag, msg)
		# If error, then errorFlag = 1, and msg will contain the error message
		# If no error, then errorFlag = 0, and msg contains the success messages
		return (self.errorFlag, msg)

	# Get vertical shift speeds
	def updateVerticalShiftSpeeds(self, acq_mode):
		msg = ""

		if acq_mode == 4: # Fast kinetics
			(ret, numvss) = self.GetNumberFKVShiftSpeeds()
			successMsg = "Number of fast kinetics VS speeds is " + str(numvss) + ".\n"
			msg += self.handleErrors(ret, "GetNumberFKVShiftSpeeds error: ", successMsg)
			self.camInfo['vss'] = []

			for i in range(numvss):
				(ret, speed) = self.GetFKVShiftSpeedF(i)
				successMsg = "Speed " + str(i) + " is {:.3} microseconds.\n".format(speed)
				msg += self.handleErrors(ret, "GetFKVShiftSpeedF error: ", successMsg)
				self.camInfo['vss'].append(speed)
		else:
			(ret, numvss) = self.GetNumberVSSpeeds()
			successMsg = "Number of vertical shift speeds is " + str(numvss) + ".\n"
			msg += self.handleErrors(ret, "GetNumberVSSpeeds error: ", successMsg)
			self.camInfo['vss'] = []

			for i in range(numvss):
				(ret, speed) = self.GetVSSpeed(i)
				successMsg = "Speed " + str(i) + " is {:.3} microseconds.\n".format(speed)
				msg += self.handleErrors(ret, "GetVSSpeed error: ", successMsg)
				self.camInfo['vss'].append(speed)
		return (self.errorFlag, msg)



	# Setup acquisition modes, get allowed EM gain range
	def armiXon(self):
		self.errorFlag = 0
		msg = ""

		ret = self.SetReadMode(KRBCAM_READ_MODE)
		successMsg = "Read mode set to " + read_modes[str(KRBCAM_READ_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetReadMode error: ", successMsg)

		if KRBCAM_USE_INTERNAL_SHUTTER:
			ret = self.SetShutter(1, KRBCAM_USE_INTERNAL_SHUTTER, self.camInfo['shutterMinT'][0], self.camInfo['shutterMinT'][1])
			successMsg = "Shutter mode set to " + shutter_modes[str(KRBCAM_USE_INTERNAL_SHUTTER)] + ".\n"
			msg += self.handleErrors(ret, "SetShutter error: ", successMsg)
		else:
			ret = self.SetShutter(1, KRBCAM_USE_INTERNAL_SHUTTER, 0, 0)
			successMsg = "Shutter mode set to " + shutter_modes[str(KRBCAM_USE_INTERNAL_SHUTTER)] + ".\n"
			msg += self.handleErrors(ret, "SetShutter error: ", successMsg)

		ret = self.SetTriggerMode(KRBCAM_TRIGGER_MODE)
		successMsg = "Trigger mode set to " + trigger_modes[str(KRBCAM_TRIGGER_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetTriggerMode error: ", successMsg)

		if KRBCAM_USE_INTERNAL_SHUTTER: # == 1 if using external shutter
			ret = self.SetFastExtTrigger(1)
			successMsg = "Trigger set to Fast External Trigger mode.\n"
			msg += self.handleErrors(ret, "SetFastExtTrigger error: ", successMsg)


		ret = self.SetEMGainMode(KRBCAM_EM_MODE)
		successMsg = "EM mode set to " + em_modes[str(KRBCAM_EM_MODE)] + ".\n"
		msg += self.handleErrors(ret, "SetEMGainMode error: ", successMsg)

		ret = self.SetEMAdvanced(KRBCAM_EM_ADVANCED)
		if KRBCAM_EM_ADVANCED:
			successMsg = "Access to EM gain of >300x is enabled.\n"
		else:
			successMsg = "Access to EM gain of >300x is disabled.\n"
		msg += self.handleErrors(ret, "SetEMAdvanced error: ", successMsg)

		(ret, range0, range1) = self.GetEMGainRange()
		self.camInfo['emGainRange'][0] = range0
		self.camInfo['emGainRange'][1] = range1

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

	# Set EM gain, AD channel, shift speeds, pre amp gain
	def setupAcquisition(self, config):
		self.errorFlag = 0
		msg = ""

		# If EM, need to use EMCCD gain register and set EMCCD gain
		if config['emEnable']:
			ret = self.SetOutputAmplifier(0)
			successMsg = "Output amplifier set to EMCCD gain register.\n"
			msg += self.handleErrors(ret, "SetOutputAmplifier error: ", successMsg)


			ret = self.SetEMCCDGain(config['emGain'])
			successMsg = "EM Gain set to " + str(config['emGain']) + ".\n"
			msg += self.handleErrors(ret, "SetEMCCDGain error: ", successMsg)
		# Otherwise, use the Conventional amplifier
		else:
			ret = self.SetOutputAmplifier(1)
			successMsg = "Output amplifier set to conventional.\n"
			msg += self.handleErrors(ret, "SetOutputAmplifier error: ", successMsg)

		# Set the AD channel
		ret = self.SetADChannel(config['adChannel'])
		successMsg = "AD Channel {} selected.\n".format(config['adChannel'])
		msg += self.handleErrors(ret, "SetADChannel error: ", successMsg)

		# Set the horizontal shift speed

		typ = 1
		if config['emEnable']:
			typ = 0
		hss = config['hss']
		ret = self.SetHSSpeed(typ, config['hss'])
		successMsg = "HShiftSpeed set to {}.\n".format(self.camInfo['hss'][0][typ][hss])
		msg += self.handleErrors(ret, "SetHSSpeed error: ", successMsg)

		# Set the pre amp gain
		pa = config['preAmpGain']
		ret = self.SetPreAmpGain(pa)
		successMsg = "Pre-Amp Gain set to {}.\n".format(self.camInfo['preAmpGain'][pa])
		msg += self.handleErrors(ret, "SetPreAmpGain error: ", successMsg)

		return (self.errorFlag, msg)


	# Set exposure times and readout times
	# Get acquisition timings
	def setupFastKinetics(self, config):
		self.errorFlag = 0
		msg = ""

		ret = self.SetAcquisitionMode(KRBCAM_ACQ_MODE_FK)
		successMsg = "Acquisition mode set to " + acq_modes[str(KRBCAM_ACQ_MODE_FK)] + ".\n"
		msg += self.handleErrors(ret, "SetAcquisitionMode error: ", successMsg)
		
		# Set the fast kinetics vertical shift speed
		(ret) = self.SetFKVShiftSpeed(config['vss'])
		successMsg = "FKVShiftSpeed set to {}.\n".format(config['vss'])
		msg += self.handleErrors(ret, "SetFKVShiftSpeed error: ", successMsg)

		# Set the exposure time
		exposure = config['expTime'] * 1e-3
		if config['binning']:
			binning = KRBCAM_BIN_SIZE
		else:
			binning = 1
		ret = self.SetFastKineticsEx(config['dy'], config['kinFrames'], exposure, 4, binning, binning, config['yOffset'])
		msg += self.handleErrors(ret, "SetFastKineticsEx error: ", "Fast Kinetics set.\n")

		# Get the FK exposure time
		(ret, realExp) = self.GetFKExposureTime()
		successMsg = "Real FK exposure time is {:.3} ms.\n".format(realExp * 1e3)
		msg += self.handleErrors(ret, "GetFKExposureTime error: ", successMsg)

		# Get the Acquisition timings
		(ret, realExp, realAcc, realKin) = self.GetAcquisitionTimings()
		successMsg = "Real (exp., acc., kin.) times are ({:.3}, {:.3}, {:.3}) ms.\n".format(realExp * 1.0e3, realAcc * 1.0e3, realKin * 1.0e3)
		msg += self.handleErrors(ret, "GetAcquisitionTimings error: ", successMsg)

		# Get the keep clean time
		(ret, keepclean) = self.GetKeepCleanTime()
		successMsg = "Keep clean time is {:.3} ms.\n".format(keepclean * 1.0e3)
		msg += self.handleErrors(ret, "GetKeepCleanTime error: ", successMsg)

		# Get the readout time
		(ret, readout) = self.GetReadOutTime()
		successMsg = "Readout time is {:.3} ms.\n".format(readout * 1.0e3)
		msg += self.handleErrors(ret, "GetReadoutTime error: ", successMsg)

		return (self.errorFlag, msg)


	def setupImage(self, config):
		self.errorFlag = 0
		msg = ""

		ret = self.SetAcquisitionMode(KRBCAM_ACQ_MODE_SINGLE)
		successMsg = "Acquisition mode set to " + acq_modes[str(KRBCAM_ACQ_MODE_SINGLE)] + ".\n"
		msg += self.handleErrors(ret, "SetAcquisitionMode error: ", successMsg)

		# Set the vertical shift speed
		(ret) = self.SetVSSpeed(config['vss'])
		successMsg = "Vertical shift speed set to {}.\n".format(config['vss'])
		msg += self.handleErrors(ret, "SetVSSpeed error: ", successMsg)
	
		# Set the exposure time
		exposure = config['expTime'] * 1e-3
		if config['binning']:
			binning = KRBCAM_BIN_SIZE
		else:
			binning = 1
		ret = self.SetExposureTime(exposure)
		msg += self.handleErrors(ret, "SetExposureTime error: ", "Exposure time set.\n")

		hstart = config['xOffset'] + 1
		hend = config['xOffset'] + config['dx']
		vstart = config['yOffset'] + 1
		vend = config['yOffset'] + config['dy']
		ret = self.SetImage(binning, binning, hstart, hend, vstart, vend)
		msg += self.handleErrors(ret, "SetImage error: ", "Image bounds set.\n")

		# Get the Acquisition timings
		(ret, realExp, realAcc, realKin) = self.GetAcquisitionTimings()
		successMsg = "Real (exp., acc., kin.) times are ({:.3}, {:.3}, {:.3}) ms.\n".format(realExp * 1.0e3, realAcc * 1.0e3, realKin * 1.0e3)
		msg += self.handleErrors(ret, "GetAcquisitionTimings error: ", successMsg)

		# Get the keep clean time
		(ret, keepclean) = self.GetKeepCleanTime()
		successMsg = "Keep clean time is {} ms.\n".format(keepclean * 1.0e3)
		msg += self.handleErrors(ret, "GetKeepCleanTime error: ", successMsg)

		# Get the readout time
		(ret, readout) = self.GetReadOutTime()
		successMsg = "Readout time is {:.3} ms.\n".format(readout * 1.0e3)
		msg += self.handleErrors(ret, "GetReadoutTime error: ", successMsg)

		return (self.errorFlag, msg)
