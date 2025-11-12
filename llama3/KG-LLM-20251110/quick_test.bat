@echo off
REM Quick setup and test script for optimized WebQSP testing

echo ============================================================
echo Optimized WebQSP Testing - Quick Setup
echo ============================================================
echo.

REM Check if tqdm is installed
python -c "import tqdm" 2>nul
if errorlevel 1 (
    echo [1/3] Installing required packages...
    pip install tqdm -q
    echo       Done!
) else (
    echo [1/3] Dependencies already installed
)

echo.
echo [2/3] Running quick test with 10 samples...
echo       This will take approximately 2-3 minutes
echo.
python test_webqsp_eperm_optimized.py 1

echo.
echo [3/3] Test complete!
echo.
echo ============================================================
echo Next steps:
echo   - Review results in test_results/quick/
echo   - Run medium test: python test_webqsp_eperm_optimized.py 2
echo   - Run full test: python test_webqsp_eperm_optimized.py 3
echo ============================================================
pause
