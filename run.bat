@echo off
setlocal
cd /d "%~dp0"
set "APP_PYTHON="
for %%P in ("%LocalAppData%\Programs\Python\Python312\python.exe" "%ProgramFiles%\Python312\python.exe" "C:\Python312\python.exe" "%LocalAppData%\Programs\Python\Python313\python.exe" "%ProgramFiles%\Python313\python.exe" "%LocalAppData%\Programs\Python\Python311\python.exe" "%ProgramFiles%\Python311\python.exe" "%ProgramFiles%\Python314\python.exe" "%LocalAppData%\Programs\Python\Python314\python.exe") do (
 if exist "%%~P" (
  "%%~P" -c "import sys,sysconfig;sys.exit(0 if sys.version_info[:2] in [(3,11),(3,12),(3,13),(3,14)] and not sysconfig.get_config_var('Py_GIL_DISABLED') else 1)" >nul 2>&1
  if not errorlevel 1 if not defined APP_PYTHON set "APP_PYTHON=%%~P"
 )
)
if not defined APP_PYTHON (
 echo Standard Python was not found. Install Python 3.12 64-bit.
 echo The free-threaded python3.14t.exe is not used by this launcher.
 echo Download: https://www.python.org/downloads/release/python-31210/
 pause
 exit /b 1
)
echo Using: %APP_PYTHON%
if not exist ".venv\Scripts\python.exe" (
 "%APP_PYTHON%" -m venv .venv
 if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" price_monitor.py
if errorlevel 1 goto fail
exit /b
:fail
echo Installation or startup failed. Send the error text.
pause
