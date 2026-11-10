.PHONY: test run build-linux build-windows build-macos deb install clean

PY       ?= python3
PYTEST   ?= $(PY) -m pytest
APP      := uniconvert

test:
	$(PYTEST) -q tests/

run:
	$(PY) -m uniconvert

install:
	$(PY) -m pip install -e .[full]

# Build Linux one-folder bundle with PyInstaller
build-linux:
	$(PY) -m PyInstaller --noconfirm --name $(APP)_linux --add-data "assets:assets" \
		--exclude-module scipy --exclude-module numba --exclude-module llvmlite \
		--exclude-module jedi --exclude-module matplotlib --exclude-module IPython \
		main.py

# Build Debian package (requires build-linux first)
deb: build-linux
	bash installers/linux/build_deb.sh

# Build Windows installer (requires makensis and mingw)
build-windows:
	powershell -ExecutionPolicy Bypass -File installers/windows/build_exe.ps1

# Build macOS dmg / app
build-macos:
	bash installers/macos/build_dmg.sh

clean:
	rm -rf build dist *.spec __pycache__ uniconvert/__pycache__ tests/__pycache__
