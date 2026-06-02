import shutil
from gi.repository import GioUnix, Gtk, GdkPixbuf, GLib
from PIL import Image as PILImage, ImageFilter
import io
from snippets import enable_blur, set_blur_regions_from_widget

def popup_with_blur(menu: Gtk.Menu, event, accuracy: int = 1):
    blur_ctx = None

    def do_blur():
        nonlocal blur_ctx
        blur_ctx = enable_blur(menu)
        def do_set_regions():
            if blur_ctx:
                set_blur_regions_from_widget(blur_ctx, menu, accuracy, erode=0)
            return False
        GLib.timeout_add(50, do_set_regions)

    menu.show_all()
    menu.popup_at_pointer(event)
    GLib.idle_add(do_blur)

def executable_exists(executable_name):
    executable_path = shutil.which(executable_name)
    return bool(executable_path)

def get_app_icon_name(app_id: str) -> str | None:
    """
    Try to resolve an app icon name from a Niri app_id.
    Attempts several common transformations before giving up.
    """
    candidates = [
        app_id,
        app_id.lower(),
        app_id.split(".")[-1],
        app_id.split(".")[-1].lower(),
        "-".join(app_id.split(".")).lower(),
    ]

    for candidate in candidates:
        try:
            app_info = GioUnix.DesktopAppInfo.new(candidate + ".desktop")
            if app_info:
                icon = app_info.get_string("Icon")
                if icon:
                    return icon
        except TypeError:
            continue

    return None

def load_blurred_pixbuf(path: str, width: int, height: int, blur_radius=10):
    try:
        img = PILImage.open(path).convert("RGBA")
        img = img.resize((width, height))
        img = img.filter(ImageFilter.GaussianBlur(blur_radius))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(buf.read())
        loader.close()

        return loader.get_pixbuf()
    except Exception:
        return None
    
def load_scaled_pixbuf(path: str, width: int, height: int):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, width, height, False
        )
    except Exception:
        return None
    
def load_cover_pixbuf(path: str, width: int, height: int):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

    src_w = pixbuf.get_width()
    src_h = pixbuf.get_height()

    scale = max(width / src_w, height / src_h)

    scaled_w = int(src_w * scale)
    scaled_h = int(src_h * scale)

    scaled = pixbuf.scale_simple(
        scaled_w,
        scaled_h,
        GdkPixbuf.InterpType.BILINEAR,
    )

    x = (scaled_w - width) // 2
    y = (scaled_h - height) // 2

    return scaled.new_subpixbuf(x, y, width, height)