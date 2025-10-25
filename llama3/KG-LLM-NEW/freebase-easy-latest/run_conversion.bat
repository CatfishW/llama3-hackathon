@echo off
REM Batch file to run the conversion estimator
echo =========================================
echo File Conversion Estimator
echo =========================================
echo.

python estimate_conversion.py
echo.
echo.
echo Press any key to continue with conversion or Ctrl+C to cancel...
pause > nul

python convert_to_parquet.py

echo.
echo =========================================
echo Conversion complete!
echo =========================================
pause
