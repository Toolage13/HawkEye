# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
This is the main .py file that is called for HawkEye. It launches a background thread to monitor and validate the
clipboard, and then passes validated clipboard data to analyze.py for processing. Then it passes the result data from
analyze.py to gui.py for presentation in the gui.
"""
import analyze
import config
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
    """
    Main app loop, watches clipboard, if valid character names are pasted, call analyze_chars()
    """
    valid = False
    recent_value = None
    while True:
        clipboard = pyperclip.paste()
        if clipboard != recent_value:
            config.OPTIONS_OBJECT.Set("show_popup", False)
            pilot_names = clipboard.splitlines()
            for name in pilot_names:
                valid = check_name_validity(name)
                if valid is False:
                    break
            if valid:
                statusmsg.push_status("Clipboard change detected...")
                recent_value = clipboard
                analyze_chars(clipboard.splitlines())
        time.sleep(0.5)  # Short sleep between loops to reduce CPU load


def check_name_validity(pilot_name):
    """
    Check if a name matches regex below
    :param pilot_name: The character name to check
    :return: Boolean of name validity
    """
    if len(pilot_name) < 3:
        return False
    regex = r"[^ 'a-zA-Z0-9-]"  # Valid EVE Online character names
    if re.search(regex, pilot_name):
        return False
    return True


def analyze_chars(pilot_names):
    """
    Send list of pilot names to analyze.main() and send it to gui.App.MyFrame.grid.sortOutlist()
    :param pilot_names: List of pilot names to process
    :param db: EveDB object to use for local queries
    """
    start_time = time.time()
    wx.CallAfter(app.MyFrame.grid.ClearGrid)
    try:
        outlist, filtered = analyze.main(pilot_names, config.OPTIONS_OBJECT.Get("pop", False))
        duration = round(time.time() - start_time, 1)
        if outlist is not None:
            # Need to use keyword args as sortOutlist can also get called
            # by event handler which would pass event object as first argument.
            wx.CallAfter(app.MyFrame.sortOutlist, outlist=outlist, duration=duration, filtered=filtered)
            config.OPTIONS_OBJECT.Set("show_popup", False)
        else:
            statusmsg.push_status("No valid character names found. Please try again...")
    except Exception:
        Logger.error("Failed to collect character information. Clipboard content was: {}".format(str(pilot_names)), exc_info=True)


app = gui.App(0)
background_thread = threading.Thread(target=watch_clpbd, daemon=True)
background_thread.start()
app.MainLoop()
