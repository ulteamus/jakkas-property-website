[CmdletBinding()]
param(
    [string]$TaskName = "PropertyBrokerLocalMySQL",
    [switch]$DryRun,
    [switch]$RunNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$startScript = (Resolve-Path (Join-Path $PSScriptRoot "start-local-mysql.ps1")).Path
$psCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$startScript`""

if ($DryRun) {
    Write-Output "Dry run: would create task '$TaskName' with command:"
    Write-Output $psCommand
    return
}

schtasks /Create /TN $TaskName /SC ONLOGON /TR $psCommand /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create scheduled task '$TaskName'."
}

Write-Output "Scheduled task '$TaskName' created for current user logon."
Write-Output "Task command: $psCommand"

if ($RunNow) {
    schtasks /Run /TN $TaskName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Task started."
    } else {
        Write-Warning "Task created, but immediate run failed. Run it manually from Task Scheduler."
    }
}
