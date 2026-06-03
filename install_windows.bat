@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  YT AI Editor — Windows Installer
echo ============================================================
echo.

:: Check Python 3.10+
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if !PYMAJ! LSS 3 (
    echo [ERROR] Python 3.10+ required. Found !PYVER!
    pause
    exit /b 1
)
if !PYMAJ! EQU 3 if !PYMIN! LSS 10 (
    echo [ERROR] Python 3.10+ required. Found !PYVER!
    pause
    exit /b 1
)
echo [OK] Python !PYVER! found.

:: Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] FFmpeg not found in PATH.
    echo   Option A: Install via winget:  winget install ffmpeg
    echo   Option B: Download from https://ffmpeg.org/download.html
    echo             and add the bin folder to your PATH.
    echo.
    echo   Recording will not work without FFmpeg. You can still use
    echo   the Process page with existing video files.
    echo.
    set /p CONT="Continue anyway? (y/n): "
    if /i "!CONT!" NEQ "y" exit /b 1
) else (
    echo [OK] FFmpeg found.
)

:: Create virtual environment
if not exist ".venv" (
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate and install
echo.
echo Installing dependencies (this may take a few minutes)...
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: Copy .env template if not present
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Created .env from template. Edit it with your API key.
    )
)

:: Create output directories
python -c "from src.utils.config import get_settings; get_settings().ensure_dirs()" 2>nul

:: Create launch script
echo @echo off > launch.bat
echo call .venv\Scripts\activate.bat >> launch.bat
echo python app.py >> launch.bat
echo [OK] Created launch.bat

echo.
echo ============================================================
echo  Installation complete!
echo ============================================================
echo.
echo  Next steps:
echo    1. Edit .env and add your ANTHROPIC_API_KEY
echo    2. Double-click launch.bat to start the app
echo       (or run: .venv\Scripts\python app.py)
echo    3. The browser opens automatically at http://localhost:8080
echo.
echo  See SETUP.md for YouTube upload and webcam setup.
echo.
pause
