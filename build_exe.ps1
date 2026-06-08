# Filename: build_exe.ps1

$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Get-Location }
Set-Location $scriptDir

$venvPath = Join-Path $scriptDir "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..."
    . $activateScript
} else {
    Write-Error "Virtual environment not found. Please run setup_and_run.ps1 first."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Installing PyInstaller..."
pip install pyinstaller

Write-Host "Building EXE using PyInstaller..."
# --onefile: Create a single executable
# --uac-admin: Request administrator privileges automatically when running the exe
# --noconsole: Hide the console window
pyinstaller --onefile --noconsole --uac-admin --name SNI-Spoofing --collect-data pydivert gui.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "==============================================="
    Write-Host "Build finished successfully!"
    Write-Host "Your executable is located in the 'dist' folder."
    Write-Host "Note: You MUST copy 'config.json' and place it next to the .exe file to run it."
    Write-Host "==============================================="
} else {
    Write-Error "Build failed with exit code $LASTEXITCODE."
}

Read-Host "Press Enter to exit"
