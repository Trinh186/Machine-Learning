@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title RFM Insight - Customer Segmentation
echo ==============================================
echo   RFM Insight - Customer Segmentation (Nhom 09)
echo ==============================================
echo.

set "PYEXE="
rem --- 1. Da co moi truong .venv tu lan chay truoc
if exist ".venv\Scripts\python.exe" set PYEXE=".venv\Scripts\python.exe"

rem --- 2. Python Launcher (py) voi phien ban 3.11 - 3.14
if not defined PYEXE for %%v in (3.14 3.13 3.12 3.11) do (
  if not defined PYEXE ( py -%%v -c "import sys" >nul 2>&1 && set "PYEXE=py -%%v" )
)

rem --- 3. Lenh python trong PATH (kiem tra >= 3.11)
if not defined PYEXE (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PYEXE=python"
)

rem --- 4. Thu muc cai dat mac dinh cua Python
if not defined PYEXE for %%v in (314 313 312 311) do (
  if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" set PYEXE="%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
)

if defined PYEXE goto run

echo Khong tim thay Python 3.11 tro len tren may nay.
echo.
choice /c YN /m "Tu dong cai Python 3.13 (can Internet, khoang 2 phut)"
if errorlevel 2 goto nopython
winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
  set PYEXE="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  goto run
)

:nopython
echo.
echo Hay cai Python 3.13 tai https://www.python.org/downloads/
echo (nho tick "Add python.exe to PATH"), sau do bam lai file CHAY_APP.bat.
pause
exit /b 1

:run
%PYEXE% launcher.py %*
if errorlevel 1 (
  echo.
  echo *** Co loi, xem thong bao phia tren. ***
  pause
  exit /b 1
)
exit /b 0
