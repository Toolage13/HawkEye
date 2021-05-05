import wx

def push_status(msg, app):
    wx.CallAfter(app.PySpy.updateStatusbar, msg)
