# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
Handles version control, static constants, resource paths, config file storage, color schema, and logging.
"""
import logging.config
import optstore
import os
import platform
import sys
import wx  # required for colour codes in DARK_MODE


Logger = logging.getLogger(__name__)

__version__ = 1.0

# Various constants
MAX_NAMES = 500  # The max number of char names to be processed
MAX_KM = 100  # Max number of killmails to process per character
ZKILL_MULTIPLIER = 1.5
ZKILL_RETRY = 50
MAX_CHUNK = 50
GUI_TITLE = "HawkEye v{}".format(__version__)
CYNO_HL_PERCENTAGE = 0.01
BLOPS_HL_PERCENTAGE = 0.01
SB_HL_PERCENTAGE = 0.1
GATECAMP_HL_PERCENTAGE = 0.25
CAP_HL_PERCENTAGE = 0.25


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)


# If application is frozen executable
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    if os.name == "posix":
        PREF_PATH = os.path.expanduser("~/Library/Preferences")
        LOG_PATH = os.path.expanduser("~/Library/Logs")

    elif os.name == "nt":
        local_path = os.path.join(os.path.expandvars("%LocalAppData%"), "HawkEye")
        if not os.path.exists(local_path):
            os.makedirs(local_path)
        PREF_PATH = local_path
        LOG_PATH = local_path

# If application is run as script
elif __file__:
    application_path = os.path.dirname(__file__)
    if platform.system() == "Linux":
        PREF_PATH = os.path.expanduser("~/.config/hawkeye")
    else:
        PREF_PATH = os.path.join(application_path, "tmp")
    if not os.path.exists(PREF_PATH):
        os.makedirs(PREF_PATH)
    LOG_PATH = PREF_PATH

GUI_CFG_FILE = os.path.join(PREF_PATH, "hawkeye.cfg")
LOG_FILE = os.path.join(LOG_PATH, "hawkeye.log")
OPTIONS_FILE = os.path.join(PREF_PATH, "hawkeye.pickle")

# Creates /kills folder in PREF_PATH if it doesn't exist
if not os.path.exists(os.path.join(PREF_PATH, 'kills/')):
    os.makedirs(os.path.join(PREF_PATH, 'kills/'))

# Persistent options object
OPTIONS_OBJECT = optstore.PersistentOptions(OPTIONS_FILE)

# Store version information
OPTIONS_OBJECT.Set("version", __version__)

# Colour Scheme
DARK_MODE = {
    "BG": wx.Colour(0, 0, 0),
    "TXT": wx.Colour(247, 160, 55),  # Yellow
    "LNE": wx.Colour(15, 15, 15),
    "LBL": wx.Colour(160, 160, 160),
    "HL1": wx.Colour(62, 157, 250),  # Blue
    "HL2": wx.Colour(237, 72, 59),  # Red
    "HL3": wx.Colour(237, 47, 218),  # Pink
    "HL4": wx.Colour(255, 255, 0),  # Bright yellow
    "HL5": wx.Colour(179, 240, 255)  # Light blue
    }

NORMAL_MODE = {
    "BG": wx.Colour(-1, -1, -1),
    "TXT": wx.Colour(45, 45, 45),
    "LNE": wx.Colour(240, 240, 240),
    "LBL": wx.Colour(32, 32, 32),
    "HL1": wx.Colour(187, 55, 46),
    "HL2": wx.Colour(38, 104, 166),
    "HL3": wx.Colour(237, 47, 218),
    "HL4": wx.Colour(0, 153, 51),  # Green,
    "HL5": wx.Colour(0, 0, 153)  # Dark blue
    }

# Logging setup
"""
For each module that requires logging, make sure to import modules
logging and this config. Then get a new logger at the beginning
of the module like this: "Logger = logging.getLogger(__name__)" and
produce log messages like this: "Logger.error("text", exc_info=True)"
"""
LOG_DETAIL = 'ERROR'

LOG_DICT = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] (%(name)s): %(message)s',
            'datefmt': '%d-%b-%Y %I:%M:%S %p'
        },
    },
    'handlers': {
        'stream_handler': {
            'level': LOG_DETAIL,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file_handler': {
            'level': LOG_DETAIL,
            'filename': LOG_FILE,
            'class': 'logging.FileHandler',
            'formatter': 'standard'
        },
        'timed_rotating_file_handler': {
            'level': LOG_DETAIL,
            'filename': LOG_FILE,
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'when': 'D',
            'interval': 7,  # Log file rolling over every week
            'backupCount': 1,
            'formatter': 'standard'
        },
    },
    'loggers': {
        '': {
            'handlers': ['timed_rotating_file_handler', 'stream_handler'],
            'level': LOG_DETAIL,
            'propagate': True
        },
    }
}
logging.config.dictConfig(LOG_DICT)
