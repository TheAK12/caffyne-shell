from snippets.applet import Applet
from .quick_settings.menus import LogoutMenu

class LogoutApplet(Applet):
    def __init__(self, parent,**kwargs):
        self.logout_menu = LogoutMenu(parent=parent, stack=self, qs=False)

        super().__init__(main_menu=self.logout_menu)
