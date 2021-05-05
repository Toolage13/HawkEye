import wx
import __main__

def push_status(msg):
    wx.CallAfter(__main__.app.PySpy.updateStatusbar, msg)