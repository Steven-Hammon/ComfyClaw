@echo off
setlocal

set "NODE_DIR=%~dp0"
set "PYTHON_EXE="

rem Expected layout for ComfyUI portable:
rem ComfyUI\python_embeded\python.exe
rem ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Nodes\requirements.bat
for %%I in ("%NODE_DIR%..\..\..\..") do set "COMFY_ROOT=%%~fI"
if exist "%COMFY_ROOT%\python_embeded\python.exe" set "PYTHON_EXE=%COMFY_ROOT%\python_embeded\python.exe"
if not defined PYTHON_EXE if exist "%COMFY_ROOT%\python_embedded\python.exe" set "PYTHON_EXE=%COMFY_ROOT%\python_embedded\python.exe"

if not defined PYTHON_EXE (
    where py >nul 2>nul
    if "%errorlevel%"=="0" set "PYTHON_EXE=py -3"
)

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if "%errorlevel%"=="0" set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo Could not find ComfyUI portable Python.
    echo Expected: "%COMFY_ROOT%\python_embeded\python.exe"
    echo Run this from ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Nodes,
    echo or install manually with the Python that launches ComfyUI:
    echo python -m pip install -r "%NODE_DIR%requirements.txt"
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
echo Installing ComfyClaw node requirements from:
echo "%NODE_DIR%requirements.txt"
echo.

%PYTHON_EXE% -m pip --version >nul 2>nul
if errorlevel 1 (
    echo pip was not found. Trying ensurepip...
    %PYTHON_EXE% -m ensurepip --upgrade
    if errorlevel 1 (
        echo Could not enable pip for this Python.
        pause
        exit /b 1
    )
)

%PYTHON_EXE% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :install_failed

%PYTHON_EXE% -m pip install -r "%NODE_DIR%requirements.txt"
if errorlevel 1 goto :install_failed

echo.
echo Checking OCR Python modules...
%PYTHON_EXE% -c "import pyautogui, PIL, numpy, pytesseract, easyocr, paddleocr; print('OCR Python modules import OK')"
if errorlevel 1 goto :install_failed

echo.
echo Checking external Tesseract executable...
%PYTHON_EXE% -c "import shutil, pathlib, sys; candidates=[shutil.which('tesseract'), r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe']; found=next((p for p in candidates if p and pathlib.Path(p).exists()), None); print(found or 'NOT FOUND'); sys.exit(0 if found else 2)"
if errorlevel 2 (
    echo.
    echo ============================================================
    echo Tesseract-OCR executable was not found.
    echo.
    echo The Python package pytesseract is only a wrapper. It cannot
    echo install the actual Tesseract OCR program for you.
    echo.
    echo Install Tesseract-OCR for Windows using ONE of these options:
    echo.
    echo Option 1 - winget:
    echo   winget install -e --id UB-Mannheim.TesseractOCR
    echo.
    echo Option 2 - installer:
    echo   Download the UB Mannheim Windows installer from:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Typical install path:
    echo   C:\Program Files\Tesseract-OCR\tesseract.exe
    echo.
    echo After installing:
    echo   1. Restart ComfyUI.
    echo   2. If the OCR node still says Tesseract is not in PATH,
    echo      add this folder to your Windows PATH:
    echo      C:\Program Files\Tesseract-OCR
    echo   3. Restart ComfyUI again after changing PATH.
    echo.
    echo PaddleOCR and EasyOCR do not need the Tesseract executable.
    echo This warning only affects the Tesseract OCR engine option.
    echo ============================================================
    echo.
) else (
    echo Tesseract executable found.
)

echo.
echo Done. Restart ComfyUI before using the OCR node.
pause
exit /b 0

:install_failed
echo.
echo Dependency installation failed.
echo Scroll up for the package that failed. PaddleOCR/PaddlePaddle and EasyOCR are large OCR packages and may take a while to install.
pause
exit /b 1
