# Build UniConvert Windows installer (.exe).
# Run on Windows with Python, PyInstaller, and NSIS installed.
#   powershell -ExecutionPolicy Bypass -File installers\windows\build_exe.ps1

$ErrorActionPreference = "Stop"
$Version = "0.1.0"

Write-Host "==> Building PyInstaller executable..."
pyinstaller --noconfirm --windowed --name uniconvert `
    --icon assets/logo.ico `
    --add-data "assets;assets" `
    uniconvert/__main__.py

Write-Host "==> Copying context-menu registry files..."
Copy-Item installers\windows\install_context_menu.reg dist\uniconvert\
Copy-Item installers\windows\uninstall_context_menu.reg dist\uniconvert\

Write-Host "==> Building NSIS installer..."
if (Get-Command makensis -ErrorAction SilentlyContinue) {
    Push-Location installers\windows
    makensis UniConvert.nsi
    Pop-Location
    New-Item -ItemType Directory -Force -Path dist\release | Out-Null
    Move-Item -Force installers\windows\UniConvert-Setup.exe "dist\release\UniConvert-$Version-Setup.exe"
    Write-Host "Built dist\release\UniConvert-$Version-Setup.exe"
} else {
    Write-Warning "NSIS (makensis.exe) not found. Install NSIS to build the Setup.exe."
    Write-Host "Falling back to a portable zip..."
    New-Item -ItemType Directory -Force -Path dist\release | Out-Null
    Compress-Archive -Force -Path dist\uniconvert\* -DestinationPath "dist\release\UniConvert-$Version-portable.zip"
}
