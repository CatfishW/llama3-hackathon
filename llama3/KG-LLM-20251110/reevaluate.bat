@echo off
REM Re-evaluate existing checkpoint with entity ID mapping

if "%~1"=="" (
    echo Usage: reevaluate.bat ^<checkpoint_file^> ^<dataset_file^> [output_file]
    echo.
    echo Example:
    echo   reevaluate.bat test_results\test_full\checkpoint_50.json data\webqsp\test_simple.json
    echo.
    pause
    exit /b 1
)

if "%~2"=="" (
    echo Error: Dataset file required
    echo Usage: reevaluate.bat ^<checkpoint_file^> ^<dataset_file^> [output_file]
    pause
    exit /b 1
)

echo ========================================
echo Re-evaluating Checkpoint
echo ========================================
echo Checkpoint: %~1
echo Dataset:    %~2
echo.

if "%~3"=="" (
    python reevaluate_with_entity_mapping.py "%~1" "%~2"
) else (
    python reevaluate_with_entity_mapping.py "%~1" "%~2" "%~3"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Re-evaluation failed!
    pause
    exit /b 1
)

echo.
pause
