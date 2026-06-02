from fabric.widgets.box import Box
from snippets import Applet
from services.singletons import brightness
from .buttons import WifiButton, BluetoothButton, AirplaneModeButton, RecordButton, DarkModeButton, KeyboardButton, NightModeButton, CaffieneButton, PowerModes
from .sliders import BrightnessSlider, VolumeSlider, MicrophoneSlider
from .header import QSHeader
from .menus import WifiMenu, BluetoothMenu, AudioMenu, KeyboardMenu, LogoutMenu, PowerMenu

class QuickSettingsMenu(Box):
    def __init__(self, stack, **kwargs):
        super().__init__(
            style_classes=["applet-menu"],
            orientation="v",
            spacing=12,
            children=[
                QSHeader(stack=stack),
                Box(
                    orientation="v",
                    spacing=12,
                    children=[
                        VolumeSlider(stack=stack),
                        BrightnessSlider() if brightness and brightness.backend else MicrophoneSlider(stack=stack),
                    ],
                ),
                Box(
                    spacing=12,
                    children=[
                        Box(
                            orientation="v",
                            spacing=12,
                            children=[
                                WifiButton(stack=stack),
                                AirplaneModeButton(),
                                DarkModeButton(),
                                Box(
                                    spacing=12,
                                    children=[
                                        NightModeButton(),
                                        CaffieneButton(),
                                    ],
                                ),
                            ],
                        ),
                        Box(
                            orientation="v",
                            spacing=12,
                            children=[
                                BluetoothButton(stack=stack),
                                KeyboardButton(stack=stack),
                                RecordButton(),
                                PowerModes(),
                            ],
                        ),
                    ],
                ),
            ],
            **kwargs,
        )

class QuickSettings(Applet):
    def __init__(self, parent, **kwargs):
        super().__init__(
            main_menu=QuickSettingsMenu(self),
            **kwargs,
        )
        self.add_menu("wifi", WifiMenu)
        # self.add_menu("bt", BluetoothMenu)
        self.add_menu("audio", AudioMenu)
        self.add_menu("kb", KeyboardMenu)
        self.add_named(LogoutMenu(self, parent),   "logout")
        self.add_menu("power", PowerMenu)