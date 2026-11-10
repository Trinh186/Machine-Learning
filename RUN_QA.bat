@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "QT_QPA_PLATFORM=offscreen"

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Khong tao duoc Python .venv. Hay cai Python 3.11 tro len.
        exit /b 1
    )
)

if not exist ".venv\tmp" mkdir ".venv\tmp"
set "TMP=%cd%\.venv\tmp"
set "TEMP=%cd%\.venv\tmp"
set "PIP_NO_CACHE_DIR=1"

".venv\Scripts\python.exe" -X utf8 -m pip install --disable-pip-version-check -r "ui_app\requirements.txt" -r "customer_segmentation\requirements.txt"
if errorlevel 1 (
    echo Cai dat thu vien that bai. Kiem tra Internet, dung luong o dia va Python.
    exit /b 1
)

".venv\Scripts\python.exe" -X utf8 -m qa.run --gui --report qa/results.json
set "code=%errorlevel%"
echo.
echo Bao cao JSON: qa\results.json
exit /b %code%