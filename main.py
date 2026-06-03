import bar
from setproctitle import setproctitle
from fabric import Application
from fabric.utils import get_relative_path, monitor_file
from services.wallpaper import WallpaperService
from utils.update_checker import check_for_updates
import services.singletons as singletons
from gi.repository import GLib

setproctitle("caffyne-shell")

app = Application("caffyne-shell")

def apply_stylesheet(*_):
    app.set_stylesheet_from_file(
        file_path=get_relative_path("./style/style.css"),
    )

style_monitor = monitor_file(get_relative_path("./style"))
style_monitor.connect("changed", apply_stylesheet)

apply_stylesheet()

GLib.timeout_add_seconds(3, lambda: (check_for_updates(), False)[1])

bar_manager = bar.initialise_bars()
singletons.bar_manager = bar_manager
wallpaper_service = WallpaperService.get_instance()
wallpaper_service.set_bar_manager(bar_manager)
app.run()