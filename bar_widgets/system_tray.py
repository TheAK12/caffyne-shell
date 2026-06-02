import gi
gi.require_version("Gray", "0.1")
from gi.repository import Gray, GdkPixbuf, Gtk, GLib
from fabric.widgets.box import Box
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from snippets import Icon
from services.singletons import edit_mode, watcher
from user_options import user_options
from utils.helpers import popup_with_blur

class TrayItem(EventBox):
    def __init__(self, item: Gray.Item, **kwargs):
        self.item = item
        super().__init__(
            style_classes=["tray-item"],
            tooltip_text=item.get_title() or "",
            child=self._build_icon(),
            **kwargs,
        )
        self.connect("button-release-event", self._on_button_press)

    def _build_icon(self) -> Image:
        pixmap = Gray.get_pixmap_for_pixmaps(self.item.get_icon_pixmaps(), 24)
        if pixmap is not None:
            pixbuf = pixmap.as_pixbuf(16, GdkPixbuf.InterpType.HYPER)
        else:
            pixbuf = Gtk.IconTheme.get_default().load_icon(
                self.item.get_icon_name(),
                16,
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
        return Image(pixbuf=pixbuf, pixel_size=16)

    def _on_button_press(self, _, event):
        if edit_mode.edit_mode:
            return False
        menu = self.item.get_menu()
        if menu:
            if user_options.theme.blur:
                popup_with_blur(menu, event)
            else:
                menu.popup_at_pointer(event)

class SystemTray(Box):
    def __init__(self, monitor_id=None, vertical=False, variant="", **kwargs):
        self._items: dict[str, TrayItem] = {}

        self.edit_overlay = Box(
            spacing=4,
            visible=False,
            style_classes=["bar-button", "edit-overlay"],
            h_align="center",
            h_expand=True,
            children=[
                Icon(icon_name="dots-three-circle-duotone"),
                Label(label="Tray"),
            ],
        )

        self.tray = Box(
            style_classes=["bar-button"],
            spacing=8,
        )

        super().__init__(
            spacing=4,
            children=[self.edit_overlay, self.tray],
            **kwargs,
        )

        self.tray.set_visible(False)
        self.connect("realize", self._on_realize)

    def _on_realize(self, *_):
        watcher.connect("item-added", self._on_item_added)
        watcher.connect("item-removed", self._on_item_removed)
        edit_mode.connect("notify::edit-mode", lambda *_: self._update_visibility())
        GLib.idle_add(self._update_visibility)

    def _on_item_added(self, _, identifier: str):
        if identifier in self._items:
            return
        item = watcher.get_item_for_identifier(identifier)
        tray_item = TrayItem(item)
        self._items[identifier] = tray_item
        self.tray.add(tray_item)
        tray_item.show()
        self._update_visibility()

    def _on_item_removed(self, _, identifier: str):
        if identifier in self._items:
            widget = self._items.pop(identifier)
            self.tray.remove(widget)
            self._update_visibility()

    def _update_visibility(self):
        has_items = bool(self._items)
        is_editing = edit_mode.edit_mode

        self.tray.set_visible(has_items)
        self.edit_overlay.set_visible(is_editing and not has_items)
        self.get_parent().get_parent().set_visible(has_items or is_editing)