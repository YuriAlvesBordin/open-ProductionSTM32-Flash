@echo off
setlocal EnableDelayedExpansion

title STM32 Flash - Setup
chcp 65001 >nul

echo.
echo  ███████╣███╗   ███╗    ██████╗ ██╗      █████╗ ███████╣██╗  ██╗
echo  ██╔════╝████╗ ████║    ██╔════╝ ██║     ██╔══██╗██╔════╝██║  ██║
echo  ███████╣██╔████╔██║    ██║  ███╗██║     ███████║███████╣███████║
echo  ╚════██╣██║╚██╔╝██║    ██║   ██║██║     ██╔══██║╚════██╣██╔══██║
echo  ███████║██║ ╚═╝ ██║    ██████╔╝███████╣██║  ██║███████║██║  ██║
echo  ╚══════╝╚═╝     ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
echo.
echo  Installation Script for Windows
echo  ─────────────────────────────────────────────────────────────────
echo.

:: ── [1/4] Check Python ───────────────────────────────────────────────────────
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

:: ── [2/4] Create virtual environment ────────────────────────────────────────
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

:: ── [3/4] Install dependencies ───────────────────────────────────────────────
echo.
echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo  WARNING: Failed to upgrade pip. Continuing anyway...
)

pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  Check your internet connection and try again.
    pause & exit /b 1
)
echo  Dependencies installed.

:: ── [4/4] Done ───────────────────────────────────────────────────────────────
echo.
echo [4/4] Setup complete.
echo.
echo  ─────────────────────────────────────────────────────────────────
echo  To run the application:
echo    .venv\Scripts\activate
echo    python src\main.py
echo  ─────────────────────────────────────────────────────────────────
echo.

:: ── Optional: build with Nuitka ───────────────────────────────────────────────
set /p BUILD_EXE="  Build a standalone executable with Nuitka? [y/N]: "
if /i "!BUILD_EXE!"=="y"   goto :check_compiler
if /i "!BUILD_EXE!"=="yes" goto :check_compiler
echo  Skipping build. Run install.bat again to build later.
goto :end

:: ── Check for C compiler (required by Nuitka) ───────────────────────────────
:check_compiler
set COMPILER_FOUND=0

:: Check for cl.exe (MSVC)
cl.exe >nul 2>&1
if not errorlevel 1 (
    set COMPILER_FOUND=1
    echo  [OK] MSVC (cl.exe) detected.
    goto :build_nuitka
)

:: Check for gcc (MinGW / MSYS2)
gcc --version >nul 2>&1
if not errorlevel 1 (
    set COMPILER_FOUND=1
    echo  [OK] GCC (MinGW) detected.
    goto :build_nuitka
)

:: Check for clang
clang --version >nul 2>&1
if not errorlevel 1 (
    set COMPILER_FOUND=1
    echo  [OK] Clang detected.
    goto :build_nuitka
)

:: No compiler found
echo.
echo  ERROR: No C compiler found. Nuitka requires one to build a standalone executable.
echo.
echo  Options:
echo    A) Install Visual C++ Build Tools (recommended):
echo       https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo       Select "Desktop development with C++" during installation.
echo.
echo    B) Install MinGW via MSYS2 (lightweight alternative):
echo       https://www.msys2.org
echo       Then run: pacman -S mingw-w64-x86_64-gcc
echo       And add C:\msys64\mingw64\bin to your PATH.
echo.
echo  After installing a compiler, run install.bat again.
echo.
pause
exit /b 1

:: ── Build ───────────────────────────────────────────────────────────────────
:build_nuitka
echo.
echo  Installing Nuitka...
pip install nuitka --quiet
if errorlevel 1 (
    echo  ERROR: Failed to install Nuitka.
    pause & exit /b 1
)
echo  Nuitka installed.

echo.
echo  Building executable... (this may take several minutes)
echo.

python -m nuitka ^
    --onefile ^
    --enable-plugin=pyqt6 ^
    --windows-console-mode=disable ^
    --windows-product-name="STM32 Flash" ^
    --windows-company-name="open-ProductionSTM32-Flash" ^
    --windows-product-version=1.0.0.0 ^
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
echo  Build complete!
echo  Executable: dist\STM32Flash.exe
echo  ─────────────────────────────────────────────────────────────────

:end
echo.
pause
endlocal
