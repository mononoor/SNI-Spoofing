# Filename: run.ps1

$ErrorActionPreference = "Stop"

# --- Administrator Privileges Check ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..."
    Start-Process powershell -ArgumentList "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Get-Location }
Set-Location $scriptDir

$venvName = "venv"
$venvPath = Join-Path $scriptDir $venvName
$mainScript = "main.py"

# --- Activate Virtual Environment ---
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..."
    try {
        . $activateScript
        Write-Host "Virtual environment activated."
    } catch {
        Write-Error "Failed to activate virtual environment. Error: $($_.Exception.Message)"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Error "Activation script not found. Please run setup first."
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Run the Application ---
Write-Host "Running the main application script: '$mainScript'..."
$mainScriptPath = Join-Path $scriptDir $mainScript
if (Test-Path $mainScriptPath) {
    try {
        & python $mainScriptPath
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
            Write-Error "Application exited with code $LASTEXITCODE."
            Read-Host "Press Enter to exit"
            exit $LASTEXITCODE
        }
    } catch {
        Write-Error "Failed to run '$mainScript'. Error: $($_.Exception.Message)"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Error "'$mainScript' not found in the project directory."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Script finished successfully."
Read-Host "Press Enter to exit"
