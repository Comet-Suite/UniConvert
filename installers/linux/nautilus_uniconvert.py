"""Nautilus (GNOME Files) extension: right-click 'Convert with UniConvert...'

Drop this file into ~/.local/share/nautilus-python/extensions/ (user install)
or /usr/share/nautilus-python/extensions/ (system install), then restart
nautilus with: nautilus -q.
"""
import os
import subprocess

try:
    from gi.repository import Nautilus, GObject
except ImportError:  # Extension host only loads if gi + nautilus-python are present
    Nautilus = None
    GObject = None


if Nautilus is not None:
    class UniConvertMenuProvider(GObject.GObject, Nautilus.MenuProvider):
        def __init__(self):
            pass

        def _menu_activate(self, menu, files):
            paths = [f.get_location().get_path() for f in files if f.get_location()]
            if not paths:
                return
            subprocess.Popen(["uniconvert"] + paths)

        def get_file_items(self, *args):
            files = args[-1]
            if not files:
                return []
            item = Nautilus.MenuItem(
                name="UniConvert::Convert",
                label="Convert with UniConvert…",
                tip="Convert selected file(s) with UniConvert",
                icon="uniconvert",
            )
            item.connect("activate", self._menu_activate, files)
            return [item]

        def get_background_items(self, *args):
            return []
