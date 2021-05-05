import logging.config
import logging
import optstore
import os
import platform
import sys
import wx  # required for colour codes in DARK_MODE


Logger = logging.getLogger(__name__)


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

LOG_FILE = os.path.join(LOG_PATH, "hawkeye.log")
GUI_CFG_FILE = os.path.join(PREF_PATH, "hawkeye.cfg")
OPTIONS_FILE = os.path.join(PREF_PATH, "hawkeye.pickle")
DB_FILE = os.path.join(PREF_PATH, "hawkeye.sqlite3")

# Persisten options object
OPTIONS_OBJECT = optstore.PersistentOptions(OPTIONS_FILE)

# Read current version from VERSION file
with open(resource_path('VERSION'), 'r') as ver_file:
    CURRENT_VER = ver_file.read().replace('\n', '')

# Clean up old GUI_CFG_FILES and OPTIONS_OBJECT keys
if os.path.isfile(GUI_CFG_FILE) and not os.path.isfile(OPTIONS_FILE):
    try:
        os.remove(GUI_CFG_FILE)
    except:
        pass
if OPTIONS_OBJECT.Get("version", 0) != CURRENT_VER:
    print("Config file erased.")
    try:
        os.remove(GUI_CFG_FILE)
    except:
        pass
    for key in OPTIONS_OBJECT.ListKeys():
        if key != "uuid":
            OPTIONS_OBJECT.Del(key)

# Store version information
OPTIONS_OBJECT.Set("version", CURRENT_VER)

# Various constants
MAX_NAMES = 500  # The max number of char names to be processed
MAX_KM = 50  # Max number of killmails to process per character
ZKILL_MULTIPLIER = 1.5
ZKILL_RETRY = 50
MAX_CHUNK = 90
GUI_TITLE = "HawkEye " + CURRENT_VER

# Colour Scheme

DARK_MODE = {
    "BG": wx.Colour(0, 0, 0),
    "TXT": wx.Colour(247, 160, 55),  # Yellow
    "LNE": wx.Colour(15, 15, 15),
    "LBL": wx.Colour(160, 160, 160),
    "HL1": wx.Colour(237, 72, 59),  # Red
    "HL2": wx.Colour(62, 157, 250),  # Blue
    "HL3": wx.Colour(237, 47, 218)  # Pink
    }

NORMAL_MODE = {
    "BG": wx.Colour(-1, -1, -1),
    "TXT": wx.Colour(45, 45, 45),
    "LNE": wx.Colour(240, 240, 240),
    "LBL": wx.Colour(32, 32, 32),
    "HL1": wx.Colour(187, 55, 46),
    "HL2": wx.Colour(38, 104, 166),
    "HL3": wx.Colour(237, 47, 218)
    }

# Logging setup
''' For each module that requires logging, make sure to import modules
logging and this config. Then get a new logger at the beginning
of the module like this: "Logger = logging.getLogger(__name__)" and
produce log messages like this: "Logger.error("text", exc_info=True)"
'''
LOG_DETAIL = 'INFO'

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
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file_handler': {
            'level': 'INFO',
            'filename': LOG_FILE,
            'class': 'logging.FileHandler',
            'formatter': 'standard'
        },
        'timed_rotating_file_handler': {
            'level': 'INFO',
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
            'level': 'INFO',
            'propagate': True
        },
    }
}
logging.config.dictConfig(LOG_DICT)
