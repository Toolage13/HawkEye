import analyze
import config
from eveDB import eveDB
import gui
import logging
import re
import threading
import time
import wx
import pyperclip
import statusmsg

Logger = logging.getLogger(__name__)


def watch_clpbd():
    db = eveDB()
    valid = False
    recent_value = None
    while True:
        clipboard = pyperclip.paste()
        if clipboard != recent_value:
            char_names = clipboard.splitlines()
            for name in char_names:
                valid = check_name_validity(name)
                if valid is False:
                    break
            if valid:
                statusmsg.push_status("Clipboard change detected...")
                recent_value = clipboard
                analyze_chars(clipboard.splitlines(), db)
        time.sleep(0.5)  # Short sleep between loops to reduce CPU load


def check_name_validity(char_name):
    if len(char_name) < 3:
        return False
    regex = r"[^ 'a-zA-Z0-9-]"  # Valid EVE Online character names
    if re.search(regex, char_name):
        return False
    return True


def analyze_chars(char_names, db):
    start_time = time.time()
    wx.CallAfter(app.PySpy.grid.ClearGrid)
    try:
        statusmsg.push_status('About to run analyze.main()...')
        outlist, filtered = analyze.main(char_names, db)
        duration = round(time.time() - start_time, 1)
        if outlist is not None:
            # Need to use keyword args as sortOutlist can also get called
            # by event handler which would pass event object as first argument.
            wx.CallAfter(
                app.PySpy.sortOutlist,
                outlist=outlist,
                duration=duration,
                filtered=filtered
                )
        else:
            statusmsg.push_status("No valid character names found. Please try again...")
    except Exception:
        Logger.error(
            "Failed to collect character information. Clipboard "
            "content was: " + str(char_names), exc_info=True
        )


config.OPTIONS_OBJECT.Set("ignoredList", [])
app = gui.App(0)
background_thread = threading.Thread(target=watch_clpbd, daemon=True)
background_thread.start()
app.MainLoop()
