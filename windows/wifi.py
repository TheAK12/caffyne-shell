from snippets.applet import Applet
from .quick_settings.menus import WifiMenu

class WifiApplet(Applet):
    def __init__(self, parent,**kwargs):
        self.wifi_menu = WifiMenu(parent=self, stack=self)

        super().__init__(main_menu=self.wifi_menu)

