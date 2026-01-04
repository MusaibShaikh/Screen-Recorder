import threading
import pystray
from PIL import Image, ImageDraw

def setup_tray(app):
    """Setup system tray icon."""
    img = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(img)
    draw.rectangle((16, 16, 48, 48), fill="red")
    menu = pystray.Menu(
        pystray.MenuItem("Show", app.show_window, default=True),
        pystray.MenuItem("Exit", app.exit_app)
    )
    tray_icon = pystray.Icon("recorder", img, "Screen Recorder", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()
    return tray_icon
