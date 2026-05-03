# PDF Studio — Build Script
# Builds the frontend and packages the desktop app

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$frontendDir = Join-Path $root "frontend"

Write-Host "Building frontend..." -ForegroundColor Cyan
Push-Location $frontendDir
npm run build
Pop-Location

Write-Host "Packaging desktop app..." -ForegroundColor Cyan
npx electron-builder

Write-Host "Done!" -ForegroundColor Green
