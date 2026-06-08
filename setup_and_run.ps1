# Filename: setup_and_run.ps1

$ErrorActionPreference = "Stop"

# --- Configuration ---
$pythonExe = "python.exe" # Name of the python executable
$venvName = "venv"
$dependencies = @(
    "pydivert",
    "pywin32",
    "customtkinter"
    # Add any other Python dependencies here, e.g., "requests"
)

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Get-Location }
Set-Location $scriptDir

# --- Check Python Installation ---
Write-Host "Checking for Python installation..."
$pythonPath = Get-Command $pythonExe -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Host "Python not found in PATH. Attempting to find it..."
    # Try common installation paths, adjust if your Python is installed elsewhere
    $possiblePythonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python310", # Example path, adjust version if needed
        "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps" # Microsoft Store Python
    )
    
    $foundPython = $false
    foreach ($path in $possiblePythonPaths) {
        $pythonExePath = Join-Path $path "$pythonExe"
        if (Test-Path $pythonExePath) {
            Write-Host "Found Python at: $pythonExePath"
            $env:PATH += ";$path"
            $foundPython = $true
            break
        }
    }
    
    if (-not $foundPython) {
        Write-Error "Python executable '$pythonExe' not found. Please ensure Python is installed and added to your system's PATH."
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "Python found in PATH: $($pythonPath.Source)"
}

# --- Create Virtual Environment ---
$venvPath = Join-Path $scriptDir $venvName

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment '$venvName'..."
    try {
        & python -m venv $venvName
        Write-Host "Virtual environment created successfully."
    } catch {
        Write-Error "Failed to create virtual environment. Error: $($_.Exception.Message)"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "Virtual environment '$venvName' already exists."
}

# --- Activate Virtual Environment ---
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..."
    try {
        # Dot-sourcing the activation script modifies the current session's environment
        . $activateScript
        Write-Host "Virtual environment activated."
    } catch {
        Write-Error "Failed to activate virtual environment. Error: $($_.Exception.Message)"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Error "Activation script not found at '$activateScript'. Cannot activate virtual environment."
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Install Dependencies ---
Write-Host "Installing dependencies..."
foreach ($dep in $dependencies) {
    Write-Host "Installing '$dep'..."
    try {
        & pip install $dep
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
            Write-Error "Failed to install '$dep' with exit code $LASTEXITCODE."
            Read-Host "Press Enter to exit"
            exit $LASTEXITCODE
        }
        Write-Host "'$dep' installed successfully."
    } catch {
        Write-Error "Failed to install '$dep'. Error: $($_.Exception.Message)"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "Setup finished successfully. You can now use run.ps1 to execute the application."
Read-Host "Press Enter to exit"
