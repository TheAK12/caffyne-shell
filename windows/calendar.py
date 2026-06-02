import datetime
import calendar
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from gi.repository import Gtk
from snippets import Icon

DAYS_OF_WEEK = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

class DayButton(Button):
    def __init__(self, day: int, in_month: bool, is_today: bool, on_select):
        self._day = day
        self._in_month = in_month

        style_classes = ["calendar-day"]
        if not in_month:
            style_classes.append("calendar-day-outside")
        if is_today:
            style_classes.append("calendar-day-today")
        self.label = Label(label=str(day))
        super().__init__(
            h_align="center",
            child=self.label,
            style_classes=style_classes,

        )
        self.label.set_xalign(0.5)
        self.label.set_justify(Gtk.Justification.CENTER)


    @property
    def day(self):
        return self._day

    @property
    def in_month(self):
        return self._in_month

    def set_selected(self, selected: bool):
        if selected:
            self.add_style_class("calendar-day-selected")
            return
        else:
            self.remove_style_class("calendar-day-selected")

class CalendarGrid(Box):
    def __init__(self, year: int, month: int, selected_day: int | None, on_day_selected):
        self._on_day_selected = on_day_selected
        self._day_buttons: list[DayButton] = []

        today = datetime.date.today()
        cal = calendar.monthcalendar(year, month)

        while len(cal) < 5:
            cal.append([0] * 7)

        first_weekday, days_in_month = calendar.monthrange(year, month)
        prev_month_date = datetime.date(year, month, 1) - datetime.timedelta(days=1)
        prev_days_in_month = prev_month_date.day

        rows = []

        header_row = Box(orientation="h", spacing=34, h_align="center", style="padding: 8px 0px;")
        for d in DAYS_OF_WEEK:
            label = Label(
                label=d,
                style_classes=["calendar-header-day"],
                width_request=32,
                h_align="center",
            )
            label.set_xalign(0.5)
            label.set_justify(Gtk.Justification.CENTER)

            header_row.add(label)
        rows.append(header_row)

        cells = []

        for i in range(first_weekday):
            d = prev_days_in_month - (first_weekday - 1 - i)
            cells.append((d, False, False))

        for d in range(1, days_in_month + 1):
            is_today = (year == today.year and month == today.month and d == today.day)
            cells.append((d, True, is_today))

        remainder = 35 - len(cells)
        for d in range(1, remainder + 1):
            cells.append((d, False, False))

        for week_idx in range(5):
            row = Box(orientation="h", spacing=16, h_align="center")
            for day_idx in range(7):
                day, in_month, is_today = cells[week_idx * 7 + day_idx]
                btn = DayButton(day, in_month, is_today, self._on_btn_clicked)
                btn.set_size_request(32, 32)
                if in_month and day == selected_day:
                    btn.set_selected(True)
                self._day_buttons.append(btn)
                row.add(btn)
            rows.append(row)

        super().__init__(
            orientation="v",
            spacing=16,
            h_align="center",
            children=rows,
        )

    def _on_btn_clicked(self, btn: DayButton):
        for b in self._day_buttons:
            b.set_selected(False)
        btn.set_selected(True)
        self._on_day_selected(btn.day)

class CalendarWidget(Box):
    def __init__(self):
        today = datetime.date.today()
        self._year = today.year
        self._month = today.month
        self._selected_day = today.day

        self._month_label = Label(
            style_classes=["calendar-month-label"],
        )

        self._grid_container = Box(
            orientation="v",
            h_align="center",
        )

        nav = CenterBox(
            h_expand=True,
            start_children=self._month_label,
            end_children=Box(spacing=12,children=[
                Button(
                    style_classes=["applet-misc-button"],
                    child=Icon(icon_name="arrow-left-duotone"),
                    on_clicked=lambda *_: self._change_month(-1),
                ),
                Button(
                    style_classes=["applet-misc-button"],
                    child=Icon(icon_name="arrow-right-duotone"),
                    on_clicked=lambda *_: self._change_month(1),
                ),
            ])
        )

        super().__init__(
            orientation="v",
            spacing=8,
            h_align="center",
            h_expand=True,
            style_classes=["applet-menu"],
            children=[nav, self._grid_container],
        )

        self._rebuild()

    def _change_month(self, delta: int):
        month = self._month + delta
        year = self._year
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1
        self._year = year
        self._month = month

        days_in_new_month = calendar.monthrange(year, month)[1]
        self._selected_day = min(self._selected_day, days_in_new_month)

        self._rebuild()

    def _on_day_selected(self, day: int):
        self._selected_day = day

    def _rebuild(self):

        for child in self._grid_container.get_children():
            self._grid_container.remove(child)
            child.destroy()

        self._month_label.set_label(
            datetime.date(self._year, self._month, 1).strftime("%B %Y")
        )

        grid = CalendarGrid(
            self._year,
            self._month,
            self._selected_day,
            self._on_day_selected,
        )
        self._grid_container.add(grid)
        self._grid_container.show_all()
    def reset(self):
        today = datetime.date.today()
        self._year = today.year
        self._month = today.month
        self._selected_day = today.day
        self._rebuild()

class CalendarApplet(Box):
    def __init__(self, parent, **kwargs):
        self._calendar = CalendarWidget()
        super().__init__(
            children=[self._calendar],
            **kwargs,
        )
        self.connect("realize", lambda *_: parent.connect("notify::visible", self._on_visibility_changed))

    def _on_visibility_changed(self, window, *_):
        if not window.get_visible():
            self._calendar.reset()