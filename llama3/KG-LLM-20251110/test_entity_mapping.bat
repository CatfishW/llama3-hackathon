@echo off
REM Test entity ID mapping functionality

echo ========================================
echo Testing Entity ID Mapping
echo ========================================
echo.

python test_entity_mapping.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Tests failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tests completed successfully!
echo ========================================
pause
