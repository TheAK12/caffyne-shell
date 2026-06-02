from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from snippets import Icon
from .hacktk.hacktk import HackedStack

class AppletPage(Box):
    def __init__(
        self,
        child: Box,
        first: bool = False,
        stack=None,
        header_right_children: Box | None = None,
        title: str | None = None,
        label: Label | None = None,
    ):

        start_children_list = []

        if not first:
            start_children_list.append(
                Button(
                    style_classes=["applet-misc-button"],
                    child=Icon(icon_name="chevron-left"),
                    on_clicked=lambda *_: stack.set_visible_child_name("main") if stack else None,
                )
            )

        start_children_list.append(
            label if label else Label(
                label=title or "",
                style="padding: 8px; font-size: 14px;",
            )
        )

        self.header = CenterBox(
            start_children=Box(
                spacing=12,
                children=start_children_list,
            ),
            end_children=header_right_children if header_right_children else None,
        )

        super().__init__(
            style_classes=["applet-menu"],
            orientation="v",
            spacing=12,
            children=[self.header, child],
        )

class Applet(HackedStack):
    def __init__(self, main_menu: AppletPage, **kwargs):
        self.main_menu = main_menu
        super().__init__(
            transition_type="slide-left-right",
            bezier_curve=(0.34, 1.3, 0.64, 1.0),
            duration=0.45,
        )
        self.add_named(main_menu, "main")
        self.connect("realize", self._on_realise)
    def _on_realise(self):
        self.get_toplevel().connect("notify::visible", self._on_visibility_changed)
    def _on_visibility_changed(self, w):
        self.set_visible_child(self.main_menu)
    def add_menu(self, name: str, menu) -> None:
        self.add_named(menu(stack=self), name)