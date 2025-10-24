@echo off
REM Qwen3 30B Optimized Launch Script for RTX 4090
REM This script provides three optimization profiles

setlocal enabledelayedexpansion

echo.
echo ================================
echo Qwen3 30B RTX 4090 Optimizer
echo ================================
echo.
echo Choose optimization profile:
echo.
echo [1] FP8 Quantization (RECOMMENDED - Best balance)
echo     Memory: ~18GB, Speed: Very Fast, Quality: Excellent
echo.
echo [2] Context Reduction Only (SIMPLEST - FP16 quality)
echo     Memory: ~23GB, Speed: Fastest, Quality: Full
echo.
echo [3] 4-bit Quantization (AGGRESSIVE - Most memory savings)
echo     Memory: ~12GB, Speed: Fast, Quality: Good
echo.
echo [4] Custom Parameters (ADVANCED)
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Launching with FP8 Quantization...
    echo Memory Usage: ~18GB
    echo.
    python vLLMDeploy.py ^
      --projects general ^
      --model qwen3-30b-a3b-instruct-2507 ^
      --quantization fp8 ^
      --max_model_len 2048 ^
      --gpu_memory_utilization 0.75 ^
      --visible_devices "0" ^
      --num_workers 12
    goto :end
)

if "%choice%"=="2" (
    echo.
    echo Launching with Context Reduction...
    echo Memory Usage: ~23GB
    echo.
    python vLLMDeploy.py ^
      --projects general ^
      --model qwen3-30b-a3b-instruct-2507 ^
      --max_model_len 2048 ^
      --gpu_memory_utilization 0.70 ^
      --visible_devices "0" ^
      --num_workers 12
    goto :end
)

if "%choice%"=="3" (
    echo.
    echo Launching with 4-bit Quantization...
    echo Memory Usage: ~12GB
    echo.
    python vLLMDeploy.py ^
      --projects general ^
      --model qwen3-30b-a3b-instruct-2507 ^
      --quantization bitsandbytes ^
      --max_model_len 2048 ^
      --gpu_memory_utilization 0.60 ^
      --visible_devices "0" ^
      --num_workers 12
    goto :end
)

if "%choice%"=="4" (
    echo.
    echo Advanced Custom Configuration
    echo.
    set /p projects="Enter projects (default: general): "
    if "!projects!"=="" set projects=general
    
    set /p max_len="Enter max_model_len (default: 2048): "
    if "!max_len!"=="" set max_len=2048
    
    set /p gpu_util="Enter gpu_memory_utilization (default: 0.75): "
    if "!gpu_util!"=="" set gpu_util=0.75
    
    set /p quant="Enter quantization method - none/fp8/bitsandbytes (default: fp8): "
    if "!quant!"=="" set quant=fp8
    
    if "!quant!"=="none" (
        python vLLMDeploy.py ^
          --projects !projects! ^
          --model qwen3-30b-a3b-instruct-2507 ^
          --max_model_len !max_len! ^
          --gpu_memory_utilization !gpu_util! ^
          --visible_devices "0" ^
          --num_workers 12
    ) else (
        python vLLMDeploy.py ^
          --projects !projects! ^
          --model qwen3-30b-a3b-instruct-2507 ^
          --quantization !quant! ^
          --max_model_len !max_len! ^
          --gpu_memory_utilization !gpu_util! ^
          --visible_devices "0" ^
          --num_workers 12
    )
    goto :end
)

echo Invalid choice. Exiting.
goto :end

:end
endlocal
pause
