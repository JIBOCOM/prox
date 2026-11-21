@echo off
rem One-time install: creates .venv and installs the Python packages.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during the install. Then run setup.bat again.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
echo.
echo Done. Next: calibrate.bat (once), then run.bat every time you play.
pause
