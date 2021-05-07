# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
Full credit to White Russsian, most of this was shamelessly stolen from him: https://github.com/Eve-PySpy/PySpy
"""
import config
import logging
import wx
import wx.adv

Logger = logging.getLogger(__name__)


def showAboutBox(parent, event=None):
    description = """
    This tool was inspired largely by PySpy and Pirate's Little Helper.
    Discord: Firehawk#0960
    IGN: Kain Tarr
    """

    try:
        with open(config.resource_path('LICENSE.txt'), 'r') as lic_file:
            license = lic_file.read()
    except:
        license = "HawkEye is licensed under the MIT License."

    info = wx.adv.AboutDialogInfo()

    info.SetName("HawkEye")
    # info.SetVersion(config.CURRENT_VER)
    info.SetDescription(description)
    info.SetCopyright('(C) 2021 Kain Tarr')
    info.SetWebSite('https://github.com/Toolage13/HawkEye')
    info.SetLicence(license)

    wx.adv.AboutBox(info)