######################
## Default settings ##
######################

KRBCAM_ACQ_MODE = 4 				# 4 is Fast Kinetics
KRBCAM_READ_MODE = 4 				# 4 is Image
KRBCAM_TRIGGER_MODE = 0				# 0 is Internal 
KRBCAM_EM_MODE = 0					# 0 is Normal
KRBCAM_EXPOSED_ROWS = 512			# Exposed rows on CCD for FK
KRBCAM_USE_INTERNAL_SHUTTER = 1		# 1 for no, 0 for yes

KRBCAM_FK_SERIES_LENGTH = 2
KRBCAM_OD_SERIES_LENGTH = 3
KRBCAM_FK_BINNING_MODE = 4
KRBCAM_N_ACC = 1
KRBCAM_BIN_SIZE = 2

KRBCAM_DEFAULT_TEMP = -5			# Celsius
KRBCAM_MIN_TEMP = -10				# Celsius
KRBCAM_MAX_TEMP = 20				# Celsius
KRBCAM_TEMP_TIMER = 2				# Celsius
KRBCAM_SAFE_TEMP = -20				# Celsius

KRBCAM_FAN_MODE = 0					# 0: full, 1: low, 2: off

KRBCAM_ACQ_TIMER = 0.5				# 0.5 s for acquisition loop
KRBCAM_LOOP_ACQ = False				# Loop acquisition?

KRBCAM_FILENAME_BASE = 'iXon_img'

default_config = {
	'exposure': '1.5',
	'xOffset': '0',
	'yOffset': '0',
	'dx': '500',
	'dy': '400',
	'emGain': '1',
	'emEnable': False,
	'savePath': 'C:\Users\KRbG2\Desktop\Kyle\\andor\python\\andor_gui\data\\',
	'binning': True
}

acq_modes = {
	'1': 'Single Scan',
	'2': 'Accumulate',
	'3': 'Kinetics',
	'4': 'Fast Kinetics',
	'5': 'Run til Abort'
}

read_modes = {
	'0': 'Full Vertical Binning',
	'1': 'Multi-Track',
	'2': 'Random-Track',
	'3': 'Single-Track',
	'4': 'Image'
}

shutter_modes = {
	'0': 'Automatic',
	'1': 'Open',
	'2': 'Closed'
}

trigger_modes = {
	'0': 'Internal',
	'1': 'External',
	'6': 'External Start',
	'7': 'External Exposure',
	'9': 'External FVB EM',
	'10': 'Software Trigger',
	'12': 'External Charge Shifting'
}

em_modes = {
	'0': 'Default mode (0-255 range)',
	'1': '0-4095 range',
	'2': 'Linear mode',
	'3': 'Real EM gain mode'
}

