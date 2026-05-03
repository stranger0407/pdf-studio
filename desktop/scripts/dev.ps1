# PDF Studio — Desktop Dev Script
# Starts the Vite dev server and Electron concurrently

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$frontendDir = Join-Path $root "frontend"
$backendDir = Join-Path $root "backend"

Write-Host "Starting Vite dev server..." -ForegroundColor Cyan
Push-Location $frontendDir
$viteProcess = Start-Process -NoNewWindow -PassThru npm -ArgumentList "run","dev"
Pop-Location

Start-Sleep -Seconds 3

$env:ELECTRON_DEV_SERVER_URL = "http://localhost:5173"
$env:BACKEND_PYTHON = "python"

Write-Host "Starting Electron..." -ForegroundColor Cyan
npx electron .

if ($viteProcess -and !$viteProcess.HasExited) {
    Stop-Process -Id $viteProcess.Id -Force
}
