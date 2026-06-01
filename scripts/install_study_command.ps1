$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$BinPath = Join-Path $ProjectRoot "bin"
$UserBinPath = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $UserBinPath | Out-Null

$LauncherCmd = Join-Path $UserBinPath "study.cmd"
$LauncherPs1 = Join-Path $UserBinPath "study-launcher.ps1"
$CliPath = Join-Path $ProjectRoot "scripts\study_cli.py"

@"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.local\bin\study-launcher.ps1" %*
exit /b %ERRORLEVEL%
"@ | Set-Content -LiteralPath $LauncherCmd -Encoding ASCII

@"
param([Parameter(ValueFromRemainingArguments=`$true)][string[]]`$RemainingArgs)
& python "$CliPath" @RemainingArgs
exit `$LASTEXITCODE
"@ | Set-Content -LiteralPath $LauncherPs1 -Encoding UTF8

$OldPs1Launcher = Join-Path $UserBinPath "study.ps1"
if (Test-Path -LiteralPath $OldPs1Launcher) {
  Remove-Item -LiteralPath $OldPs1Launcher -Force
}

$CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$Parts = @()
if ($CurrentUserPath) {
  $Parts = $CurrentUserPath -split ';' | Where-Object { $_ }
}

function Add-PathPart {
  param([string]$PathToAdd)
  $resolvedToAdd = Resolve-Path -LiteralPath $PathToAdd
  foreach ($Part in $script:Parts) {
    $resolvedPart = Resolve-Path -LiteralPath $Part -ErrorAction SilentlyContinue
    if ($resolvedPart -and [string]::Equals($resolvedPart.Path, $resolvedToAdd.Path, [System.StringComparison]::OrdinalIgnoreCase)) {
      return
    }
  }
  $script:Parts = @($resolvedToAdd.Path) + $script:Parts
}

Add-PathPart $UserBinPath
Add-PathPart $BinPath

$NewPath = ($Parts | Where-Object { $_ }) -join ';'
[Environment]::SetEnvironmentVariable("Path", $NewPath, "User")

Write-Host "Study command installed."
Write-Host "Launcher: $LauncherCmd"
Write-Host "Open a new PowerShell window and run: study hacker"
