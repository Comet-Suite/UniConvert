"""Standalone launcher for PyInstaller. Calls the GUI entry point."""
import sys
from uniconvert.gui import run

if __name__ == "__main__":
    sys.exit(run())
