@echo off
REM First-run setup for a portable UniConvert install on Windows.
REM Extracts the bundled embedded Python and installs required wheels.
setlocal
cd /d "%~dp0"
if not exist python\python.exe (
  echo [UniConvert] Extracting embedded Python...
  powershell -NoProfile -Command "Expand-Archive -Force -Path python-3.12.8-embed-amd64.zip -DestinationPath python"
  powershell -NoProfile -Command "(Get-Content python\python312._pth) -replace '#import site','import site' | Set-Content python\python312._pth"
  echo [UniConvert] Installing pip and dependencies...
  python\python.exe get-pip.py --no-warn-script-location
  python\python.exe -m pip install --no-warn-script-location --no-index --find-links wheels -r requirements.txt
  echo [UniConvert] Setup complete. Run UniConvert.exe to start.
)
endlocal
