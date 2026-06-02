from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from services.singletons import wm
from utils.helpers import get_app_icon_name

FALLBACK_ICON = "application-x-executable-symbolic"
FALLBACK_TITLE = "Desktop"

class NiriClientTitle(Box):
    def __init__(self, monitor_id, vertical, variant, **kwargs):
        self.icon = Image(
            style_classes=["icon"],
            icon_name=FALLBACK_ICON,
            icon_size=18,
        )
        self.label = Label(ellipsization="end", max_chars_width=15)

        self.label.set_yalign(0.55)
        wm.active_window.connect(
            "notify::app-id",
            lambda obj, _: self.icon.set_from_icon_name(
                get_app_icon_name(obj.app_id) or FALLBACK_ICON,
                18,
            ),
        )
        wm.active_window.connect(
            "notify::title",
            lambda obj, _: self.label.set_label(obj.title or FALLBACK_TITLE),
        )

        self.icon.set_from_icon_name(
            get_app_icon_name(wm.active_window.app_id) or FALLBACK_ICON,
            18,
        )
        self.label.set_label(wm.active_window.title or FALLBACK_TITLE)

        super().__init__(
            style_classes=["bar-button"],
            spacing=4,
            children=[self.icon, self.label],
            **kwargs,
        )

