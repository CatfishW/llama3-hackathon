# Prompt Portal C++ Backend - Build Script (Windows PowerShell)
# ============================================================

param(
    [switch]$Clean,
    [switch]$Release,
    [switch]$Run
)

$ErrorActionPreference = "Stop"

$BuildType = if ($Release) { "Release" } else { "Debug" }
$BuildDir = "build"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Prompt Portal C++ Backend - Build Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check for required tools
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Check CMake
try {
    $cmakeVersion = cmake --version | Select-Object -First 1
    Write-Host "  CMake: $cmakeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: CMake not found. Please install CMake 3.16+" -ForegroundColor Red
    Write-Host "  Download from: https://cmake.org/download/" -ForegroundColor Yellow
    exit 1
}

# Check for compiler
$compiler = "Not found"
if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
    $compiler = "MSVC (Visual Studio)"
} elseif (Get-Command g++.exe -ErrorAction SilentlyContinue) {
    $compiler = "MinGW g++"
} elseif (Get-Command clang++.exe -ErrorAction SilentlyContinue) {
    $compiler = "Clang++"
}
Write-Host "  Compiler: $compiler" -ForegroundColor Green

if ($compiler -eq "Not found") {
    Write-Host "  WARNING: No C++ compiler found. Build may fail." -ForegroundColor Yellow
    Write-Host "  Install Visual Studio Build Tools or MinGW-w64" -ForegroundColor Yellow
}

# Clean if requested
if ($Clean -and (Test-Path $BuildDir)) {
    Write-Host ""
    Write-Host "[2/5] Cleaning build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BuildDir
    Write-Host "  Build directory cleaned." -ForegroundColor Green
}

# Create build directory
Write-Host ""
Write-Host "[3/5] Creating build directory..." -ForegroundColor Yellow
if (-not (Test-Path $BuildDir)) {
    New-Item -ItemType Directory -Path $BuildDir | Out-Null
}
Write-Host "  Build directory ready." -ForegroundColor Green

# Configure with CMake
Write-Host ""
Write-Host "[4/5] Configuring with CMake ($BuildType)..." -ForegroundColor Yellow
Push-Location $BuildDir
try {
    cmake .. -DCMAKE_BUILD_TYPE=$BuildType
    if ($LASTEXITCODE -ne 0) {
        throw "CMake configuration failed"
    }
    Write-Host "  Configuration complete." -ForegroundColor Green
} catch {
    Write-Host "  ERROR: CMake configuration failed." -ForegroundColor Red
    Pop-Location
    exit 1
}

# Build
Write-Host ""
Write-Host "[5/5] Building project..." -ForegroundColor Yellow
try {
    cmake --build . --config $BuildType --parallel
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed"
    }
    Write-Host "  Build complete!" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Build failed." -ForegroundColor Red
    Pop-Location
    exit 1
}

Pop-Location

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Build Successful!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Executable location:" -ForegroundColor Yellow
Write-Host "  $BuildDir\$BuildType\prompt_portal_cpp.exe" -ForegroundColor White
Write-Host ""
Write-Host "To run the server:" -ForegroundColor Yellow
Write-Host "  cd $BuildDir\$BuildType" -ForegroundColor White
Write-Host "  .\prompt_portal_cpp.exe" -ForegroundColor White
Write-Host ""

# Run if requested
if ($Run) {
    Write-Host "Starting server..." -ForegroundColor Yellow
    $exePath = Join-Path $BuildDir "$BuildType\prompt_portal_cpp.exe"
    if (Test-Path $exePath) {
        Push-Location (Split-Path $exePath)
        & $exePath
        Pop-Location
    } else {
        # Try without Release/Debug subdirectory
        $exePath = Join-Path $BuildDir "prompt_portal_cpp.exe"
        if (Test-Path $exePath) {
            Push-Location $BuildDir
            & .\prompt_portal_cpp.exe
            Pop-Location
        } else {
            Write-Host "ERROR: Executable not found at expected location" -ForegroundColor Red
        }
    }
}

