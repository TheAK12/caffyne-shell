from snippets.applet import Applet
from .quick_settings.menus import AudioMenu, BluetoothMenu, PowerMenu, KeyboardMenu, LogoutMenu

class AudioApplet(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(main_menu=AudioMenu(stack=None), **kwargs)

class BluetoothApplet(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(main_menu=BluetoothMenu(stack=None), **kwargs)

class PowerApplet(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(main_menu=PowerMenu(stack=None), **kwargs)

class KeyboardApplet(Applet):
    def __init__(self, *args, **kwargs):
        super().__init__(main_menu=KeyboardMenu(stack=None), **kwargs)