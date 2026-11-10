import os, subprocess
try:
    from gi.repository import Nautilus, GObject
except ImportError:
    Nautilus = None
if Nautilus is not None:
    class UniConvertMenuProvider(GObject.GObject, Nautilus.MenuProvider):
        def __init__(self): pass
        def _menu_activate(self, menu, files):
            paths = [f.get_location().get_path() for f in files if f.get_location()]
            if paths: subprocess.Popen(["uniconvert"] + paths)
        def get_file_items(self, *args):
            files = args[-1]
            if not files: return []
            item = Nautilus.MenuItem(name="UniConvert::Convert",
                label="Convert with UniConvert\u2026",
                tip="Convert selected file(s) with UniConvert", icon="uniconvert")
            item.connect("activate", self._menu_activate, files)
            return [item]
