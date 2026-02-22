<#
Open Project helper (Windows PowerShell)
Usage: Right-click and Run with PowerShell, or run from PowerShell prompt:
    .\open_project.ps1
This script activates the venv, starts the Flask app in a new window, and opens the browser.
#>
param(
  [string]$Host = '127.0.0.1',
  [int]$Port = 5000
)

$venvActivate = Join-Path $PSScriptRoot 'venv\Scripts\Activate.ps1'
if (-Not (Test-Path $venvActivate)) {
  Write-Host "Virtualenv activate script not found at $venvActivate" -ForegroundColor Yellow
  Write-Host "If your venv is elsewhere, edit this script to point to it." -ForegroundColor Yellow
}
else {
  Write-Host 'Activating venv...'
  & $venvActivate
}

$python = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-Not (Test-Path $python)) { $python = 'python' }

Write-Host 'Starting Flask app in a new window...'
$startArgs = "-NoExit -Command `"cd '$PSScriptRoot'; & '$python' 'app.py'`""
Start-Process powershell -ArgumentList $startArgs

Start-Sleep -Seconds 1
Start-Process "http://$Host`:$Port/"
Write-Host "Opened http://$Host`:$Port/ in your default browser." -ForegroundColor Green