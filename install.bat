@echo off
setlocal EnableDelayedExpansion

title STM32 Flash - Setup
chcp 65001 >nul

echo.
echo  ████████╗███╗   ███╗    ██████╗ ██╗      █████╗ ███████╗██╗  ██╗
echo  ██╔════╝████╗ ████║    ██╔════╝ ██║     ██╔══██╗██╔════╝██║  ██║
echo  ███████╗██╔████╔██║    █████╗   ██║     ███████║███████╗███████║
echo  ╚════██║██║╚██╔╝██║    ██╔══╝   ██║     ██╔══██║╚════██║██╔══██║
echo  ███████║██║ ╚═╝ ██║    ██║      ███████╗██║  ██║███████║██║  ██║
echo  ╚══════╝╚═╝     ╚═╝    ╚═╝      ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
echo.
echo  Installation Script for Windows
echo  ─────────────────────────────────────────────────────────────────
echo.

:: ── Check for Python ───────────────────────────────────────────────────────
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found in PATH.
    echo  Download it at https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Found: !PYVER!

:: ── Check Python version >= 3.10 ────────────────────────────────────────────
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER_NUM=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER_NUM!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if !PY_MAJOR! LSS 3 (
    echo  ERROR: Python 3.10+ is required. Found !PYVER_NUM!.
    pause & exit /b 1
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 10 (
    echo  ERROR: Python 3.10+ is required. Found !PYVER_NUM!.
    pause & exit /b 1
)

:: ── Create virtual environment ───────────────────────────────────────────────
echo.
echo [2/4] Creating virtual environment (.venv)...
if exist .venv (
    echo  .venv already exists, skipping creation.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause & exit /b 1
    )
    echo  Created .venv
)

:: ── Upgrade pip silently ─────────────────────────────────────────────────────
echo.
echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo  WARNING: Failed to upgrade pip. Continuing anyway...
)

pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  Check your internet connection and try again.
    pause & exit /b 1
)
echo  PyQt6 installed successfully.

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo [4/4] Setup complete.
echo.
echo  ─────────────────────────────────────────────────────────────────
echo  To run the application:
echo    .venv\Scripts\activate
echo    python src\main.py
echo  ─────────────────────────────────────────────────────────────────
echo.

:: ── Optional: build executable with Nuitka ──────────────────────────────────
set /p BUILD_EXE="Build a standalone executable with Nuitka? [y/N]: "
if /i "!BUILD_EXE!"=="y" goto :build_nuitka
if /i "!BUILD_EXE!"=="yes" goto :build_nuitka
echo  Skipping build. Run install.bat again or use build.bat to build later.
goto :end

:build_nuitka
echo.
echo  Installing Nuitka...
pip install nuitka --quiet
if errorlevel 1 (
    echo  ERROR: Failed to install Nuitka.
    pause & exit /b 1
)

echo  Building executable... (this may take several minutes)
echo.
python -m nuitka ^
    --onefile ^
    --enable-plugin=pyqt6 ^
    --windows-console-mode=disable ^
    --windows-product-name="STM32 Flash" ^
    --windows-company-name="open-ProductionSTM32-Flash" ^
    --windows-product-version=2.0.0.0 ^
    --output-dir=dist ^
    --output-filename=STM32Flash ^
    --include-data-dir=config=config ^
    src/main.py

if errorlevel 1 (
    echo.
    echo  ERROR: Build failed. Check output above for details.
    pause & exit /b 1
)

echo.
echo  ─────────────────────────────────────────────────────────────────
echo  Build successful!
echo  Executable: dist\STM32Flash.exe
echo  ─────────────────────────────────────────────────────────────────

:end
echo.
pause
endlocal
