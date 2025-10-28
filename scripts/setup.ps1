param(
    [string]$PythonCommand = "python",
    [string]$VenvPath = ".venv",
    [string]$RequirementsFile = "requirements.txt"
)

$ErrorActionPreference = "Stop"

function Write-Info($Message) {
    Write-Host "[info] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[warn] $Message" -ForegroundColor Yellow
}

Write-Info "verifying python command"
if (-not (Get-Command $PythonCommand -ErrorAction SilentlyContinue)) {
    throw "python command '$PythonCommand' not found. install Python 3.12 and retry."
}

if (-not (Test-Path $VenvPath)) {
    Write-Info "creating virtual environment at $VenvPath"
    & $PythonCommand -m venv $VenvPath
}
else {
    Write-Info "virtual environment already exists"
}

$ActivatePython = Join-Path $VenvPath "Scripts/python.exe"
if (-not (Test-Path $ActivatePython)) {
    throw "expected python executable at $ActivatePython"
}

Write-Info "upgrading pip"
& $ActivatePython -m pip install --upgrade pip

if (Test-Path $RequirementsFile) {
    Write-Info "installing dependencies from $RequirementsFile"
    & $ActivatePython -m pip install -r $RequirementsFile
}
else {
    Write-Warn "requirements file '$RequirementsFile' not found. skipping package installation."
}

Write-Info "setup complete"
Write-Info "activate environment with `& $VenvPath\Scripts\Activate.ps1` before running agents"
