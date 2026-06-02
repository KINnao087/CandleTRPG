param(
  [string]$OutputDir = "release\CandleTRPG-LAN",
  [switch]$SkipWheelhouse
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $repoRoot "frontend"
$backendDir = Join-Path $repoRoot "backend"
$packageTemplateDir = Join-Path $repoRoot "scripts\package"
$outputPath = Join-Path $repoRoot $OutputDir
$frontendDist = Join-Path $frontendDir "dist"

function Ensure-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command not found: $name"
  }
}

function Get-PythonCommand {
  if (Get-Command "py" -ErrorAction SilentlyContinue) {
    return [pscustomobject]@{ Exe = "py"; Args = @("-3") }
  }
  if (Get-Command "python" -ErrorAction SilentlyContinue) {
    return [pscustomobject]@{ Exe = "python"; Args = @() }
  }
  if (Get-Command "python3" -ErrorAction SilentlyContinue) {
    return [pscustomobject]@{ Exe = "python3"; Args = @() }
  }
  throw "Required command not found: Python 3.11+. Install Python and make sure it is in PATH."
}

Ensure-Command "npm"
$pythonCommand = Get-PythonCommand

Write-Host "Building frontend..."
Push-Location $frontendDir
try {
  if (-not (Test-Path "node_modules")) {
    npm ci
  }
  npm run build
}
finally {
  Pop-Location
}

if (-not (Test-Path $frontendDist)) {
  throw "Frontend dist was not generated: $frontendDist"
}

if (Test-Path $outputPath) {
  $resolvedOutput = Resolve-Path $outputPath
  if (-not $resolvedOutput.Path.StartsWith($repoRoot.Path)) {
    throw "Refusing to remove output outside repository: $resolvedOutput"
  }
  Remove-Item -LiteralPath $resolvedOutput.Path -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

Write-Host "Copying backend..."
Copy-Item -Path $backendDir -Destination (Join-Path $outputPath "backend") -Recurse

Write-Host "Copying frontend dist..."
New-Item -ItemType Directory -Force -Path (Join-Path $outputPath "frontend_dist") | Out-Null
Copy-Item -Path (Join-Path $frontendDist "*") -Destination (Join-Path $outputPath "frontend_dist") -Recurse

Write-Host "Copying runtime files..."
Copy-Item -Path (Join-Path $repoRoot "requirements.txt") -Destination (Join-Path $outputPath "requirements.txt")
Copy-Item -Path (Join-Path $packageTemplateDir "start.bat") -Destination (Join-Path $outputPath "start.bat")
Copy-Item -Path (Join-Path $packageTemplateDir "README_RELEASE.md") -Destination (Join-Path $outputPath "README.md")
Copy-Item -Path (Join-Path $packageTemplateDir "env.example") -Destination (Join-Path $outputPath ".env.example")

if (-not $SkipWheelhouse) {
  Write-Host "Downloading Python wheels for offline install..."
  New-Item -ItemType Directory -Force -Path (Join-Path $outputPath "wheelhouse") | Out-Null
  & $pythonCommand.Exe @($pythonCommand.Args) -m pip download -r (Join-Path $outputPath "requirements.txt") -d (Join-Path $outputPath "wheelhouse")
}

Write-Host ""
Write-Host "Package generated:"
Write-Host $outputPath
Write-Host ""
Write-Host "Send this folder to users. They can run start.bat."
