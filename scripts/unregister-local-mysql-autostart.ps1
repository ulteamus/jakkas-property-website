[CmdletBinding()]
param(
    [string]$TaskName = "PropertyBrokerLocalMySQL",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($DryRun) {
    Write-Output "Dry run: would delete task '$TaskName'."
    return
}

schtasks /Delete /TN $TaskName /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to delete scheduled task '$TaskName'."
}

Write-Output "Scheduled task '$TaskName' removed."
