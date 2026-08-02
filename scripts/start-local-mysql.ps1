[CmdletBinding()]
param(
    [string]$MySqlBinDir = "$env:ProgramFiles\MySQL\MySQL Server 8.4\bin",
    [string]$DataDir = "",
    [string]$UndoDir = "",
    [int]$Port = 0,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPath = Join-Path $repoRoot ".env"

function Get-DotEnvValue {
    param([string]$Name)

    if (-not (Test-Path $envPath)) {
        return $null
    }

    $line = Select-String -Path $envPath -Pattern "^$Name=(.*)$" | Select-Object -First 1
    if (-not $line) {
        return $null
    }

    $raw = $line.Matches[0].Groups[1].Value.Trim()
    if ($raw.StartsWith('"') -and $raw.EndsWith('"')) {
        return $raw.Trim('"')
    }
    return $raw
}

function Test-PortListening {
    param([int]$LocalPort)

    try {
        $connections = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
        return [bool]$connections
    } catch {
        return $false
    }
}

$mysqlHost = Get-DotEnvValue -Name "MYSQL_HOST"
if ([string]::IsNullOrWhiteSpace($mysqlHost)) {
    $mysqlHost = "127.0.0.1"
}

if ($Port -le 0) {
    $rawPort = Get-DotEnvValue -Name "MYSQL_PORT"
    if ([string]::IsNullOrWhiteSpace($rawPort)) {
        $Port = 3306
    } else {
        $parsedPort = 0
        if (-not [int]::TryParse($rawPort, [ref]$parsedPort) -or $parsedPort -le 0) {
            throw "Invalid MYSQL_PORT value in .env: '$rawPort'"
        }
        $Port = $parsedPort
    }
}

if ([string]::IsNullOrWhiteSpace($DataDir)) {
    $DataDir = Join-Path $repoRoot ".mysql84-alt2"
}

if ([string]::IsNullOrWhiteSpace($UndoDir)) {
    $UndoDir = Join-Path $repoRoot ".mysql84-undo"
}

$MySqlBinDir = $MySqlBinDir.TrimEnd("\")
$mysqldPath = Join-Path $MySqlBinDir "mysqld.exe"
$baseDir = (Split-Path -Parent $MySqlBinDir).TrimEnd("\")

if (-not (Test-Path $mysqldPath)) {
    throw "mysqld.exe not found at '$mysqldPath'. Update -MySqlBinDir to match your installation."
}

if (-not (Test-Path $DataDir)) {
    throw "Data directory '$DataDir' does not exist."
}

if (-not (Test-Path $UndoDir)) {
    New-Item -ItemType Directory -Path $UndoDir -Force | Out-Null
}

if ($mysqlHost -notin @("127.0.0.1", "localhost", "::1")) {
    Write-Warning "MYSQL_HOST is '$mysqlHost'. This helper starts local mysqld for localhost only."
}

if (Test-PortListening -LocalPort $Port) {
    Write-Output "MySQL already listening on port $Port. Nothing to do."
    return
}

$args = @(
    "--basedir=""$baseDir""",
    "--datadir=""$DataDir""",
    "--innodb_undo_directory=""$UndoDir""",
    "--port=$Port",
    "--bind-address=127.0.0.1",
    "--console"
)

Write-Output "Starting local MySQL..."
Write-Output "$mysqldPath $($args -join ' ')"

if ($DryRun) {
    Write-Output "Dry run completed; no process started."
    return
}

$proc = Start-Process -FilePath $mysqldPath -ArgumentList $args -PassThru

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500

    if (Test-PortListening -LocalPort $Port) {
        Write-Output "MySQL is now listening on port $Port (PID $($proc.Id))."
        return
    }

    if ($proc.HasExited) {
        break
    }
}

if ($proc.HasExited) {
    throw "mysqld exited early with code $($proc.ExitCode). Check your datadir/undo settings."
}

Write-Warning "mysqld started as PID $($proc.Id), but port $Port is not reachable yet. Check process logs."
