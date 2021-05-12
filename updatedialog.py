# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
Full credit to White Russsian, most of this was shamelessly stolen from him: https://github.com/Eve-PySpy/PySpy
"""
import config
import logging
import requests
import wx
import wx.adv

Logger = logging.getLogger(__name__)

url = "https://raw.githubusercontent.com/Toolage13/HawkEye/main/version"
headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'HawkEye, Author: Kain Tarr'}
current_version = float(requests.get(url, headers=headers).content.decode())

def CheckVersion():
    if current_version > config.__version__:
        return True
    return False


def showUpdateBox(parent, event=None):
    description = """
    You are running HawkEye version {}    
    The latest version is {}
    Download using link below.
    """.format(config.__version__, current_version)

    info = wx.adv.AboutDialogInfo()

    info.SetName("Update")
    info.SetDescription(description)
    info.SetCopyright('(C) 2021 Kain Tarr')
    info.SetWebSite('https://github.com/Toolage13/HawkEye')

    wx.adv.AboutBox(info)
