@echo off
REM Batch script to run WebQSP tests in different modes

echo ========================================
echo WebQSP Test Modes
echo ========================================
echo.
echo Available modes:
echo   1. EPERM (with KG) - default mode
echo   2. Pure LLM (no KG) - baseline comparison
echo   3. Both (comparison) - run both modes
echo.

if "%1"=="" (
    echo Usage: test_webqsp_modes.bat [mode] [num_samples] [checkpoint_interval]
    echo.
    echo Arguments:
    echo   mode: eperm, pure-llm, or both
    echo   num_samples: number of samples to test ^(default: 100^)
    echo   checkpoint_interval: save checkpoint every N samples ^(default: 100^)
    echo.
    echo Examples:
    echo   test_webqsp_modes.bat eperm 100 50
    echo   test_webqsp_modes.bat pure-llm 100 50
    echo   test_webqsp_modes.bat both 50 25
    echo.
    exit /b 1
)

set MODE=%1
set NUM_SAMPLES=%2
set CHECKPOINT_INTERVAL=%3

if "%NUM_SAMPLES%"=="" set NUM_SAMPLES=100
if "%CHECKPOINT_INTERVAL%"=="" set CHECKPOINT_INTERVAL=100

echo Running in %MODE% mode with %NUM_SAMPLES% samples
echo Checkpoint interval: %CHECKPOINT_INTERVAL%
echo.

python test_webqsp_eperm.py --mode %MODE% --num_samples %NUM_SAMPLES% --checkpoint_interval %CHECKPOINT_INTERVAL% --max_kg_size 100

echo.
echo ========================================
echo Test completed!
echo ========================================
