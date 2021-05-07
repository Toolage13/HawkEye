# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
Full credit to White Russsian, most of this was shamelessly stolen from him: https://github.com/Eve-PySpy/PySpy
"""
import __main__
import wx

def push_status(msg):
    wx.CallAfter(__main__.app.MyFrame.updateStatusbar, msg)
