param(
    [string]$ConfigPath = "config/agents.config.json",
    [string]$VenvPath = ".venv",
    [string]$ManagerUrl = "http://127.0.0.1:8000",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Info($Message) { Write-Host "[info] $Message" -ForegroundColor Cyan }
function Write-Warn($Message) { Write-Host "[warn] $Message" -ForegroundColor Yellow }
function Write-ErrorLine($Message) { Write-Host "[error] $Message" -ForegroundColor Red }

if (-not (Test-Path $ConfigPath)) { throw "configuration file '$ConfigPath' not found" }

$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

$PythonPath = Join-Path $VenvPath "Scripts/python.exe"
if (-not (Test-Path $PythonPath)) { Write-Warn "python executable not found at $PythonPath. run scripts/setup.ps1 first." }

if (-not $Config.agents) { Write-ErrorLine "No agents configured in $ConfigPath"; exit 1 }

# Base port for agent services
$basePort = 8100

$i = 0
foreach ($Agent in $Config.agents) {
    $AgentId = $Agent.id
    $EntryPoint = $Agent.entryPoint
    # If agent config provides an explicit port, use it; otherwise use index-based port
    if ($Agent.port) {
        $port = $Agent.port
    } else {
        $port = $basePort + $i
    }

    Write-Info "Preparing MCP service for agent '$AgentId' on port $port"

    if (-not $EntryPoint) {
        Write-Warn "agent '$AgentId' has no entryPoint defined in config - skipping"
        $i++
        continue
    }

    if (-not (Test-Path $EntryPoint)) {
        Write-Warn "entry point file '$EntryPoint' not found. skipping launch."
        $i++
        continue
    }

    if ($DryRun) {
        Write-Info "dry-run: would execute $PythonPath -m agents.mcp_service --agent-id $AgentId --config $ConfigPath --port $port --manager-url $ManagerUrl"
        $i++
        continue
    }

    if (-not (Test-Path $PythonPath)) {
        Write-ErrorLine "cannot run agent '$AgentId' because python path is missing"
        $i++
        continue
    }

    # Launch agent service in background
    $args = "-m agents.mcp_service --agent-id $AgentId --config $ConfigPath --port $port --manager-url $ManagerUrl"
    Write-Info "launching agent service '$AgentId'"

    Start-Process -FilePath $PythonPath -ArgumentList $args -NoNewWindow -WindowStyle Hidden

    $i++
}

Write-Info "Launched $i agent services (MCP-style)."
