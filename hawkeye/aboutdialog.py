from hawkeye import config
import logging
import wx
import wx.adv

Logger = logging.getLogger(__name__)


def showAboutBox(parent, event=None):
    description = """
    This this is trash!
    """

    try:
        with open(config.resource_path('LICENSE.txt'), 'r') as lic_file:
            license = lic_file.read()
    except:
        license = "HawkEye is licensed under the MIT License."

    info = wx.adv.AboutDialogInfo()

    info.SetName("HawkEye")
    info.SetVersion(config.CURRENT_VER)
    info.SetDescription(description)
    info.SetCopyright('(C) 2021 Kain Tarr')
    info.SetWebSite('https://github.com/Eve-PySpy/PySpy')
    info.SetLicence(license)

    wx.adv.AboutBox(info)