import analyze
from eveDB import eveDB
import logging
import re
import threading
import time
import wx
import pyperclip
import gui
import statusmsg

Logger = logging.getLogger(__name__)


def watch_clpbd():
    valid = False
    recent_value = None
    db = eveDB()
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
        outlist = analyze.main(char_names, db)
        duration = round(time.time() - start_time, 1)
        if outlist is not None:
            # Need to use keyword args as sortOutlist can also get called
            # by event handler which would pass event object as first argument.
            wx.CallAfter(
                app.PySpy.sortOutlist,
                outlist=outlist,
                duration=duration
                )
        else:
            statusmsg.push_status(
                "No valid character names found. Please try again..."
                )
    except Exception:
        Logger.error(
            "Failed to collect character information. Clipboard "
            "content was: " + str(char_names), exc_info=True
        )


app = gui.App(0)  # Has to be defined before background thread starts.
background_thread = threading.Thread(target=watch_clpbd, daemon=True)
background_thread.start()
app.MainLoop()
