import __main__
import wx

def push_status(msg):
    wx.CallAfter(__main__.app.PySpy.updateStatusbar, msg)
