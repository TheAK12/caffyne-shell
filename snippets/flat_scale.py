import gi
import cairo
from typing import Callable, Iterable, Literal, TypedDict
from fabric.widgets.widget import Widget
from fabric.utils.helpers import clamp
from .animator import Animator
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, GObject

class FlatScaleStyle(TypedDict):
    slider_color: Gdk.RGBA
    slider_height: float
    slider_thickness: float
    top_gap: float
    bottom_gap: float
    corner_radius: float
    progress_color: Gdk.RGBA
    progress_thickness: float
    trough_color: Gdk.RGBA
    trough_thickness: float
    background_color: Gdk.RGBA

class FlatScale(Gtk.DrawingArea, Widget):
    """
    A Cairo-drawn linear scale widget for Fabric.

    Styled via CSS sub-nodes (slider, trough, highlight), mirroring
    CircularScale's gadget context approach. Use margin-top/margin-bottom
    on the slider node to create a gap between the slider and the arcs.

    Example CSS:
        .flat-scale slider {
            background-color: var(--primary);
            min-height: 16px;   /* slider length along the track */
            min-width: 16px;    /* slider thickness across the track */
            border-radius: 8px;
            margin-top: 4px;    /* gap above slider handle */
            margin-bottom: 4px; /* gap below slider handle */
        }
        .flat-scale trough {
            background-color: alpha(var(--primary), 0.3);
            border-width: 6px;  /* trough thickness */
        }
        .flat-scale trough highlight {
            background-color: var(--primary);
            border-width: 6px;  /* progress thickness */
        }
    """

    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(
        self,
        value: float = 0.5,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.05,
        orientation: Literal["horizontal", "vertical"] | Gtk.Orientation = Gtk.Orientation.HORIZONTAL,
        on_value_changed: Callable[["FlatScale", float], None] | None = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Gtk.DrawingArea.__init__(self)
        Widget.__init__(
            self,
            name=name,
            visible=visible,
            all_visible=all_visible,
            style=style,
            style_classes=style_classes,
            tooltip_text=tooltip_text,
            tooltip_markup=tooltip_markup,
            h_align=h_align,
            v_align=v_align,
            h_expand=h_expand,
            v_expand=v_expand,
            size=size,
            **kwargs,
        )

        self._value = clamp(value, min_value, max_value)
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._dragging = False
        self._hovering = False
        self._cached_style: FlatScaleStyle | None = None
        self._gadget_classes: dict[Gtk.StyleContext, frozenset[str] | None] = {}
        self._anim_initialized = False
        self._anim_press = Animator(
            bezier_curve=(0.4, 0.0, 0.2, 1.0),
            duration=0.1,
            min_value=16.0,
            max_value=16.0,
            tick_widget=self,
        )
        self._scroll_accumulator = 0.0
        self._anim_press.connect("notify::value", lambda *_: self.queue_draw())
        if isinstance(orientation, str):
            self._orientation = (
                Gtk.Orientation.HORIZONTAL
                if orientation == "horizontal"
                else Gtk.Orientation.VERTICAL
            )
        else:
            self._orientation = orientation

        self._highlight_ctx = self.do_create_gadget_context("highlight")
        self._trough_ctx = self.do_create_gadget_context("trough")
        self._slider_ctx = self.do_create_gadget_context("slider")

        self.get_style_context().add_class("flat-scale")

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )

        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("scroll-event", self._on_scroll)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)
        self.connect("realize", self._on_realize)

        self.show_all()
        if on_value_changed:
            self.connect("value-changed", on_value_changed)

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self.set_value(v)

    def set_value(self, value: float) -> None:
        new = clamp(value, self._min_value, self._max_value)
        if new != self._value:
            self._value = new
            self.emit("value-changed", self._value)
            self.queue_draw()

    def get_value(self) -> float:
        return self._value

    def _on_realize(self, _widget) -> None:
        state = self.get_state_flags()
        self._gadget_classes[self._slider_ctx] = None
        self.do_update_gadget_path(self._slider_ctx, "slider")
        default_size = self._slider_ctx.get_property("min-height", state)
        self._anim_press.min_value = default_size
        self._anim_press.max_value = default_size
        self._anim_press.value = default_size
        self._anim_initialized = True
    def do_create_gadget_context(self, node_name: str) -> Gtk.StyleContext:
        ctx = Gtk.StyleContext()
        ctx.set_parent(self.get_style_context())
        ctx.set_screen(self.get_screen())
        self._gadget_classes[ctx] = None
        ctx.connect("changed", lambda *_: self.do_update_gadget_path(ctx, node_name))
        self.do_update_gadget_path(ctx, node_name)
        return ctx

    def do_update_gadget_path(self, context: Gtk.StyleContext, node_name: str) -> None:
        parent_ctx = self.get_style_context()
        current_classes = frozenset(parent_ctx.list_classes())

        if current_classes != self._gadget_classes[context]:
            self._gadget_classes[context] = current_classes
            new_path = parent_ctx.get_path().copy()
            for cls in list(new_path.iter_list_classes(-1)):
                if cls not in current_classes:
                    new_path.iter_remove_class(-1, cls)
            for cls in current_classes:
                if not new_path.iter_has_class(-1, cls):
                    new_path.iter_add_class(-1, cls)
            new_path.append_type(GObject.TYPE_NONE)
            new_path.iter_set_object_name(-1, node_name)
            context.set_path(new_path)

        context.set_state(self.get_state_flags())
        self._cached_style = None
        self.queue_draw()

    def do_get_border_width(self, context: Gtk.StyleContext, state: Gtk.StateFlags) -> float:
        border = context.get_border(state)
        return max(
            border.top,
            border.bottom,
            border.left,
            border.right,
            context.get_property("min-width", state),
            context.get_property("min-height", state),
        )

    def do_resolve_style(self) -> FlatScaleStyle:
        if self._cached_style is not None:
            return self._cached_style

        state = self.get_state_flags()
        self._cached_style = FlatScaleStyle(
            slider_color=self._slider_ctx.get_background_color(state),
            slider_height=self._slider_ctx.get_property("min-height", state),
            slider_thickness=self._slider_ctx.get_property("min-width", state),
            top_gap=self._slider_ctx.get_property("margin-top", state),
            bottom_gap=self._slider_ctx.get_property("margin-bottom", state),
            left_gap=self._slider_ctx.get_property("margin-left", state),
            right_gap=self._slider_ctx.get_property("margin-right", state),
            corner_radius=self._slider_ctx.get_property("border-radius", state),
            progress_color=self._highlight_ctx.get_background_color(state),
            progress_thickness=self.do_get_border_width(self._highlight_ctx, state),
            trough_color=self._trough_ctx.get_background_color(state),
            trough_thickness=self.do_get_border_width(self._trough_ctx, state),
            background_color=self.get_style_context().get_background_color(state),
        )
        return self._cached_style

    def do_normalize_value(self) -> float:
        value_range = self._max_value - self._min_value
        if value_range == 0:
            return 0.0
        return clamp((self._value - self._min_value) / value_range, 0.0, 1.0)

    def _is_horizontal(self) -> bool:
        return self._orientation == Gtk.Orientation.HORIZONTAL

    def _value_from_coords(self, x: float, y: float) -> float:
        """Convert pointer coordinates to a value in [min, max]."""
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        if self._is_horizontal():
            ratio = clamp(x / width, 0.0, 1.0)
        else:
            ratio = clamp(1.0 - (y / height), 0.0, 1.0)

        return self._min_value + ratio * (self._max_value - self._min_value)

    def do_draw_rounded_rect(
        self,
        cr: cairo.Context,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
    ) -> None:
        import math
        r = min(radius, width / 2, height / 2)
        if r <= 0:
            cr.rectangle(x, y, width, height)
            return

        cr.new_sub_path()
        cr.move_to(x + r, y)
        cr.line_to(x + width - r, y)
        cr.arc(x + width - r, y + r,         r, -math.pi / 2, 0)
        cr.line_to(x + width, y + height - r)
        cr.arc(x + width - r, y + height - r, r,  0,           math.pi / 2)
        cr.line_to(x + r, y + height)
        cr.arc(x + r,         y + height - r, r,  math.pi / 2, math.pi)
        cr.line_to(x, y + r)
        cr.arc(x + r,         y + r,          r,  math.pi,     3 * math.pi / 2)
        cr.close_path()

    def do_draw(self, cr: cairo.Context) -> bool:
        styles = self.do_resolve_style()

        width = self.get_allocated_width()
        height = self.get_allocated_height()
        horizontal = self._is_horizontal()
        trough_thickness = styles["trough_thickness"]
        progress_thickness = styles["progress_thickness"]
        slider_height = self._anim_press.value
        slider_thickness = self._anim_press.value
        left_gap = styles["left_gap"]
        right_gap = styles["right_gap"]
        top_gap = styles["top_gap"]
        bottom_gap = styles["bottom_gap"]
        corner_radius = styles["corner_radius"]

        normalized = self.do_normalize_value()

        if horizontal:
            track_y = height / 2
            track_start = 0.0
            track_end = float(width)
            track_length = track_end - track_start

            slider_half = slider_height / 2
            slider_cx = track_start + slider_half + normalized * (track_length - slider_height)
            slider_cy = track_y

            trough_x = slider_cx + slider_half + right_gap
            trough_w = max(track_end - trough_x, 0.0)
            if trough_w > 0:
                Gdk.cairo_set_source_rgba(cr, styles["trough_color"])
                self.do_draw_rounded_rect(
                    cr,
                    trough_x, track_y - trough_thickness / 2,
                    trough_w, trough_thickness,
                    trough_thickness / 2,
                )
                cr.fill()

            progress_w = max(slider_cx - slider_half - left_gap - track_start, 0.0)
            if progress_w > 0:
                Gdk.cairo_set_source_rgba(cr, styles["progress_color"])
                self.do_draw_rounded_rect(
                    cr,
                    track_start, track_y - progress_thickness / 2,
                    progress_w, progress_thickness,
                    progress_thickness / 2,
                )
                cr.fill()

            Gdk.cairo_set_source_rgba(cr, styles["slider_color"])
            self.do_draw_rounded_rect(
                cr,
                slider_cx - slider_half,
                slider_cy - slider_thickness / 2,
                slider_height, slider_thickness,
                corner_radius,
            )
            cr.fill()

        else:
            track_x = width / 2
            track_start = 0.0
            track_end = float(height)
            track_length = track_end - track_start

            slider_half = slider_height / 2
            slider_cy = track_end - slider_half - normalized * (track_length - slider_height)
            slider_cx = track_x

            trough_y = track_start
            trough_h = max(slider_cy - slider_half - top_gap - track_start, 0.0)
            if trough_h > 0:
                Gdk.cairo_set_source_rgba(cr, styles["trough_color"])
                self.do_draw_rounded_rect(
                    cr,
                    track_x - trough_thickness / 2, trough_y,
                    trough_thickness, trough_h,
                    trough_thickness / 2,
                )
                cr.fill()

            progress_y = slider_cy + slider_half + bottom_gap
            progress_h = max(track_end - progress_y, 0.0)
            if progress_h > 0:
                Gdk.cairo_set_source_rgba(cr, styles["progress_color"])
                self.do_draw_rounded_rect(
                    cr,
                    track_x - progress_thickness / 2, progress_y,
                    progress_thickness, progress_h,
                    progress_thickness / 2,
                )
                cr.fill()

            Gdk.cairo_set_source_rgba(cr, styles["slider_color"])
            self.do_draw_rounded_rect(
                cr,
                slider_cx - slider_thickness / 2,
                slider_cy - slider_half,
                slider_thickness, slider_height,
                corner_radius,
            )
            cr.fill()

        return False

    def _on_button_press(self, _widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            self._dragging = True
            self._update_state_flags()
            self.set_value(self._value_from_coords(event.x, event.y))
        return True

    def _on_button_release(self, _widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            self._dragging = False
            self._update_state_flags()
        return False

    def _on_motion(self, _widget, event: Gdk.EventMotion) -> bool:
        if self._dragging:
            self.set_value(self._value_from_coords(event.x, event.y))
        return True

    def _on_scroll(self, _widget, event: Gdk.EventScroll) -> bool:
        if event.direction == Gdk.ScrollDirection.UP:
            self.set_value(self._value + self._step)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.set_value(self._value - self._step)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            self._scroll_accumulator += event.delta_y * -10
            if abs(self._scroll_accumulator) >= 1.0:
                steps = int(self._scroll_accumulator)
                self.set_value(self._value + steps * self._step)
                self._scroll_accumulator -= steps
        return True
    
    def _on_enter(self, _widget, _event) -> bool:
        self._hovering = True
        self._update_state_flags()
        return False

    def _on_leave(self, _widget, _event) -> bool:
        self._hovering = False
        self._dragging = False
        self._update_state_flags()
        return False
        
    def _update_state_flags(self) -> None:
        ctx = self.get_style_context()

        if self._hovering:
            ctx.add_class("hover")
        else:
            ctx.remove_class("hover")

        if self._dragging:
            ctx.add_class("active")
        else:
            ctx.remove_class("active")

        self._gadget_classes[self._slider_ctx] = None
        self.do_update_gadget_path(self._slider_ctx, "slider")
        self._cached_style = None

        state = self.get_state_flags()
        target = self._slider_ctx.get_property("min-height", state)

        if self._anim_initialized:
            self._anim_press.min_value = self._anim_press.value
            self._anim_press.max_value = target
            self._anim_press.play()

        self.queue_draw()