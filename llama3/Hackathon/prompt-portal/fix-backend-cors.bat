@echo off
REM Quick fix for backend CORS to allow domain access

echo 🔧 Fixing backend CORS configuration...
echo.

cd /d "%~dp0backend"

REM Check if .env exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)

REM Backup existing .env
echo Backing up current .env...
copy .env .env.backup.%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2% >nul

REM Set comprehensive CORS origins
set CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173

echo Updating CORS_ORIGINS in .env...

REM Create a temporary Python script to update the .env file
echo import re > update_env.py
echo. >> update_env.py
echo with open('.env', 'r') as f: >> update_env.py
echo     content = f.read() >> update_env.py
echo. >> update_env.py
echo cors_line = 'CORS_ORIGINS=%CORS_ORIGINS%' >> update_env.py
echo. >> update_env.py
echo if 'CORS_ORIGINS=' in content: >> update_env.py
echo     content = re.sub(r'CORS_ORIGINS=.*', cors_line, content) >> update_env.py
echo else: >> update_env.py
echo     content += '\n' + cors_line >> update_env.py
echo. >> update_env.py
echo with open('.env', 'w') as f: >> update_env.py
echo     f.write(content) >> update_env.py
echo. >> update_env.py
echo print('✓ CORS configuration updated!') >> update_env.py

python update_env.py
del update_env.py

echo.
echo CORS now allows:
echo   - https://lammp.agaii.org
echo   - http://lammp.agaii.org
echo   - http://localhost:3000
echo   - http://127.0.0.1:3000
echo   - http://localhost:3001
echo   - http://127.0.0.1:3001
echo   - http://localhost:5173
echo   - http://127.0.0.1:5173
echo.
echo ⚠️  You need to restart the backend for changes to take effect
echo.
pause
