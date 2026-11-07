@echo off
setlocal
cd /d "%~dp0"
echo.
echo === Waterforce Screen Control builder ===
echo.
echo Step 1 of 3: installing the pieces the app needs...
py -3.12 -m pip install --upgrade pyinstaller pystray hidapi pillow imageio-ffmpeg
if errorlevel 1 goto fail
echo.
echo Step 2 of 3: building the program (this takes a minute or two)...
py -3.12 -m PyInstaller --noconsole --onefile --name WaterforceScreenControl --icon icon.ico --collect-all imageio_ffmpeg --hidden-import pystray._win32 --hidden-import aorus_lcd --hidden-import aorus_ui --hidden-import wsc_logo aorus_lcd_app.py
if errorlevel 1 goto fail
echo.
echo Step 3 of 3: done.
echo Your program is here:  %~dp0dist\WaterforceScreenControl.exe
echo Copy it to a permanent folder (for example C:\Tools\WaterforceScreenControl) before you turn on "Start with Windows".
echo.
pause
exit /b 0
:fail
echo.
echo Something went wrong. Scroll up to read the last error and send it to me.
pause
exit /b 1
