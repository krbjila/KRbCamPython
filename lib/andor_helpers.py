######################
## Default settings ##
######################

KRBCAM_ACQ_MODE_FK = 4					# 4 is Fast kinetics
KRBCAM_ACQ_MODE_SINGLE = 1				# 1 is Single

KRBCAM_ACQ_MODE = KRBCAM_ACQ_MODE_FK	# 4 is Fast Kinetics

KRBCAM_READ_MODE = 4 				# 4 is Image

KRBCAM_TRIGGER_MODE = 1				# 0 is Internal, 1 is External
KRBCAM_EM_MODE = 0					# 0 is Normal
KRBCAM_EXPOSED_ROWS = 512			# Exposed rows on CCD for FK

KRBCAM_USE_INTERNAL_SHUTTER = 1		# 1 for no, 0 for yes

KRBCAM_FK_SERIES_LENGTH = 2
KRBCAM_OD_SERIES_LENGTH_FK = 3			# 3 for absorption imaging
KRBCAM_OD_SERIES_LENGTH_IMAGE = 2	# 2 for fluorescence
KRBCAM_FK_BINNING_MODE = 4
KRBCAM_N_ACC = 1
KRBCAM_BIN_SIZE = 2

KRBCAM_DEFAULT_TEMP = -50			# Celsius
KRBCAM_MIN_TEMP = -70				# Celsius
KRBCAM_MAX_TEMP = 20				# Celsius
KRBCAM_TEMP_TIMER = 2				# Seconds
KRBCAM_SAFE_TEMP = -20				# Celsius

KRBCAM_FAN_MODE = 2					# 0: full, 1: low, 2: off

KRBCAM_ACQ_TIMER = 0.5				# 0.5 s for acquisition loop
KRBCAM_LOOP_ACQ = True				# Loop acquisition?

KRBCAM_FILENAME_BASE_IMAGE = 'iXon_img'
KRBCAM_FILENAME_BASE_FK = 'iXon_fk'

KRBCAM_VERBOSE_FLAG = True

KRBCAM_OD_MAX = 8

default_config = {
	'exposure': '.01',
	'xOffset': '0',
	'yOffset': '0',
	'dx': '500',
	'dy': str(KRBCAM_EXPOSED_ROWS),
	'emGain': '1',
	'emEnable': False,
	'savePath': 'C:\\Users\\Ye Lab\\Desktop\\KRbCamPython\\data\\',
	'vss': 3,
	'preAmpGain': 0,
	'adChannel': 0,
	'hss': 0,
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

