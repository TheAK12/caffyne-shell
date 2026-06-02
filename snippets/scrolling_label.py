import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GLib, PangoCairo
from snippets.animator import Animator
from fabric.widgets.widget import Widget

class ScrollingLabel(Gtk.DrawingArea, Widget):
    def __init__(
        self,
        label: str = "---",
        pixels_per_second: float = 50.0,
        max_width: int = 200,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes=None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align=None,
        v_align=None,
        h_expand: bool = False,
        v_expand: bool = False,
        size=None,
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)
        Widget.__init__(
            self,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )

        self._label = label
        self.max_width_limit = max_width
        self.set_halign(Gtk.Align.START)

        self._text_w = 0
        self._scrolling = False
        self._pixels_per_second = pixels_per_second
        self._gap = 48

        self.animator = (
            Animator(
                bezier_curve=(0.0, 0.0, 1.0, 1.0),
                duration=1.0,
                min_value=0.0,
                max_value=1.0,
                tick_widget=self,
                notify_value=lambda *_: self._on_value_changed(),
            )
            .build()
            .unwrap()
        )

        self.set_events(
            self.get_events()
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)
        self.show_all()

    def get_label(self) -> str:
        return self._label

    def set_label(self, new_label: str):
        if self._label != str(new_label):
            self._label = str(new_label)
            self._reset()
            self.queue_resize()

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str):
        self.set_label(value)

    def _scroll_duration(self) -> float:
        return (self._text_w + self._gap) / self._pixels_per_second
    
    def _on_enter(self, *_):
        if self._text_w > self.get_allocated_width():
            self._scrolling = True
            self.animator.pause()
            self.animator.value = 0.0
            self.animator.duration = self._scroll_duration()
            self.animator.play()

    def _on_leave(self, *_):
        self._scrolling = False

    def _on_value_changed(self):
        self.queue_draw()

        if self._scrolling and self.animator.value >= 1.0:
            GLib.idle_add(self._loop)

    def _loop(self):
        if self._scrolling:
            self.animator.pause()
            self.animator.value = 0.0
            self.animator.duration = self._scroll_duration()
            self.animator.play()
        return GLib.SOURCE_REMOVE

    def _reset(self):
        self._scrolling = False
        self.animator.pause()
        self.animator.value = 0.0

    def do_get_preferred_width(self):
        layout = self.create_pango_layout(self._label)
        style_context = self.get_style_context()
        layout.set_font_description(style_context.get_font(Gtk.StateFlags.NORMAL))
        text_w, _ = layout.get_pixel_size()
        natural = min(text_w, self.max_width_limit)
        return natural, natural

    def do_get_preferred_height(self):
        layout = self.create_pango_layout(self._label)
        style_context = self.get_style_context()
        layout.set_font_description(style_context.get_font(Gtk.StateFlags.NORMAL))
        _, text_h = layout.get_pixel_size()
        return text_h, text_h

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        style_context = self.get_style_context()
        rgba = style_context.get_color(Gtk.StateFlags.NORMAL)
        font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)

        layout = self.create_pango_layout(self._label)
        layout.set_font_description(font_desc)
        text_w, text_h = layout.get_pixel_size()
        self._text_w = text_w
        fade_width = 24

        cr.rectangle(0, 0, width, height)
        cr.clip()

        y_pos = (height - text_h) / 2
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)

        if text_w > width:
            slot = text_w + self._gap
            x_offset = -slot * self.animator.value

            cr.move_to(x_offset, y_pos)
            PangoCairo.show_layout(cr, layout)

            cr.move_to(x_offset + slot, y_pos)
            PangoCairo.show_layout(cr, layout)
        else:
            cr.move_to(0.0, y_pos)
            PangoCairo.show_layout(cr, layout)