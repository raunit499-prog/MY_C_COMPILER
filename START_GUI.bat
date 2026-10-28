@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import tkinter,sys; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto TryPython
py -3 "%~dp0gui\app.py"
if errorlevel 1 goto Failed
exit /b 0

:TryPython
python -c "import tkinter,sys; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto MissingPython
python "%~dp0gui\app.py"
if errorlevel 1 goto Failed
exit /b 0

:MissingPython
echo Python 3.10 or newer with Tkinter is required.
echo Install Python for Windows from https://www.python.org/downloads/windows/
echo Include Tcl/Tk during setup, then double-click START_GUI.bat again.
pause
exit /b 1

:Failed
echo.
echo The GUI stopped with an error. Please read the message above.
pause
exit /b 1
