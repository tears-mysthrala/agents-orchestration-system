param(
    [string]$ConfigPath = "config/agents.config.json",
    [string]$VenvPath = ".venv",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Info($Message) {
    Write-Host "[info] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[warn] $Message" -ForegroundColor Yellow
}

function Write-ErrorLine($Message) {
    Write-Host "[error] $Message" -ForegroundColor Red
}

if (-not (Test-Path $ConfigPath)) {
    throw "configuration file '$ConfigPath' not found"
}

$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$LogDir = $Config.runtime.logDirectory
if (-not $LogDir) {
    $LogDir = "logs"
}

if (-not (Test-Path $LogDir)) {
    Write-Info "creating log directory at $LogDir"
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$PythonPath = Join-Path $VenvPath "Scripts/python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-Warn "python executable not found at $PythonPath. run scripts/setup.ps1 first."
}

Write-Info "loaded configuration for project $($Config.metadata.project)"

foreach ($Agent in $Config.agents) {
    $AgentId = $Agent.id
    $EntryPoint = $Agent.entryPoint
    Write-Info "preparing agent '$AgentId' using $($Agent.defaultModel)"

    if (-not $EntryPoint) {
        Write-Warn "agent '$AgentId' has no entry point defined"
        continue
    }

    if (-not (Test-Path $EntryPoint)) {
        Write-Warn "entry point file '$EntryPoint' not found. skipping launch."
        continue
    }

    $Arguments = @($EntryPoint, "--agent-id", $AgentId, "--config", $ConfigPath)
    if ($DryRun) {
        Write-Info "dry-run: would execute $PythonPath $($Arguments -join ' ')"
        continue
    }

    if (-not (Test-Path $PythonPath)) {
        Write-ErrorLine "cannot run agent '$AgentId' because python path is missing"
        continue
    }

    Write-Info "launching agent '$AgentId'"
    & $PythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorLine "agent '$AgentId' exited with code $LASTEXITCODE"
    }
}
