<#
    Baut die Windows-Anwendung.

    Ergebnis:
      packaging\dist\VintedAutoListingTool\VintedAutoListingTool.exe
      installer_output\VintedAutoListingTool-Setup.exe   (wenn Inno Setup installiert ist)

    Aufruf:  powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Virtuelle Umgebung vorbereiten" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
$python = Join-Path $root ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements-dev.txt

if (-not $SkipTests) {
    Write-Host "==> Tests ausführen" -ForegroundColor Cyan
    $env:QT_QPA_PLATFORM = "offscreen"
    & $python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Tests fehlgeschlagen – Build abgebrochen." }
    Remove-Item Env:\QT_QPA_PLATFORM
}

Write-Host "==> Alte Build-Artefakte entfernen" -ForegroundColor Cyan
Remove-Item -Recurse -Force "packaging\build", "packaging\dist" -ErrorAction SilentlyContinue

Write-Host "==> PyInstaller-Build" -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean `
    --distpath "packaging\dist" --workpath "packaging\build" `
    "packaging\VintedAutoListingTool.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller-Build fehlgeschlagen." }

$exe = "packaging\dist\VintedAutoListingTool\VintedAutoListingTool.exe"
if (-not (Test-Path $exe)) { throw "Die EXE wurde nicht erzeugt: $exe" }
Write-Host "==> EXE erstellt: $exe" -ForegroundColor Green

if (-not $SkipInstaller) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($iscc) {
        Write-Host "==> Installer bauen" -ForegroundColor Cyan
        & $iscc "packaging\installer.iss"
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup ist fehlgeschlagen." }
        Write-Host "==> Installer erstellt: installer_output\VintedAutoListingTool-Setup.exe" -ForegroundColor Green
    }
    else {
        Write-Warning "Inno Setup 6 wurde nicht gefunden – nur die EXE wurde gebaut."
        Write-Warning "Download: https://jrsoftware.org/isdl.php"
    }
}

Write-Host "Fertig." -ForegroundColor Green
