######################
## Default settings ##
######################

#########################################################################################
############# Don't change stuff below this line unless you mean it! ####################
#########################################################################################

KRBCAM_ACQ_MODE_FK = 4					# 4 is Fast kinetics
KRBCAM_ACQ_MODE_SINGLE = 1				# 1 is Single

KRBCAM_ACQ_MODE = KRBCAM_ACQ_MODE_FK	# 4 is Fast Kinetics

KRBCAM_READ_MODE = 4 					# 4 is Image

KRBCAM_TRIGGER_MODE = 1					# 0 is Internal, 1 is External
KRBCAM_EM_MODE = 0						# 0 is Normal
KRBCAM_EXPOSED_ROWS = 512				# Exposed rows on CCD for FK

KRBCAM_USE_INTERNAL_SHUTTER = 1			# 1 for no, 0 for yes

KRBCAM_FK_SERIES_LENGTH = 2
KRBCAM_OD_SERIES_LENGTH_FK = 3			# 3 for absorption imaging
KRBCAM_OD_SERIES_LENGTH_IMAGE = 2		# 2 for fluorescence
KRBCAM_FK_BINNING_MODE = 4
KRBCAM_N_ACC = 1
KRBCAM_BIN_SIZE = 2

KRBCAM_DEFAULT_TEMP = -20				# Celsius
KRBCAM_MIN_TEMP = -70					# Celsius
KRBCAM_MAX_TEMP = 20					# Celsius
KRBCAM_TEMP_TIMER = 4					# Seconds
KRBCAM_SAFE_TEMP = -20					# Celsius

KRBCAM_FAN_MODE = 2						# 0: full, 1: low, 2: off

if KRBCAM_TRIGGER_MODE == 1:
	KRBCAM_ACQ_TIMER = 0.1				# 0.1 s for external trigger acquisition loop
else:
	KRBCAM_ACQ_TIMER = 0.3				# 0.3 s for internal trigger acquisition loop
KRBCAM_LOOP_ACQ = True					# Loop acquisition?

KRBCAM_FILENAME_BASE_IMAGE = 'ixon_img_'
KRBCAM_FILENAME_BASE_FK = 'ixon_'

KRBCAM_VERBOSE_FLAG = True

KRBCAM_OD_MAX = 10

KRBCAM_LOCAL_SAVE_PATH = 'C:\\Users\\Ye Lab\\Desktop\\KRbCamPython\\data\\'

with open('./lib/ip.txt') as f:
	ip_str = f.read(100)
KRBCAM_REMOTE_SAVE_PATH = '\\\\' + ip_str + '\\krbdata\\data\\' # PolarKRB's IP address
KRBCAM_SAVE_PATH_SUFFIX = '{0.year}\\{0:%m}\\{0.year}{0:%m}{0:%d}\\Andor\\' # e.g. "2019\01\20190101\Andor\"
KRBCAM_DEFAULT_SAVE_PATH = KRBCAM_REMOTE_SAVE_PATH

#########################################################################################
############# Don't change stuff above this line unless you mean it! ####################
#########################################################################################

##################################
##### GUI default parameters #####
##################################

default_config = {
	'exposure': '1.0',
	'xOffset': '0',
	'yOffset': '0',
	'dx': '500',
	'dy': str(KRBCAM_EXPOSED_ROWS),
	'emGain': '1',
	'emEnable': False,
	'savePath': KRBCAM_DEFAULT_SAVE_PATH,
	'vss': 2,
	'preAmpGain': 0,
	'adChannel': 0,
	'hss': 0,
	'binning': True,
	'saveFiles': True
}

KRBCAM_AUTOSCALE_PERCENTILES = [0.2, 99.8]

#####################################
######### Dicts for lookups #########
#####################################

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

