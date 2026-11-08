

Scroll down for the installation video

# Waterforce Screen Control

A small, free Windows app that controls the LCD screen on the **Gigabyte AORUS WATERFORCE X 360** liquid cooler, so you don't need Gigabyte Control Center (GCC) running.

> **Unofficial.** This project is not made by, affiliated with, or endorsed by Gigabyte. "Gigabyte", "AORUS" and "Waterforce" belong to their owners. Use at your own risk.

## What it does

- Switch what the cooler's screen shows (temperatures, fan, pump, liquid, your own pictures and animations).
- Show your own **GIFs, videos and pictures** and your own **text** (with font, slant and rotation).
- Show temperatures in **°C or °F**.
- Colours and appearance of the app itself, and your own app logo.
- Runs quietly in the **system tray**, remembers your last settings and re-applies them when Windows starts.
- Optional one-click setup of **LibreHardwareMonitor** (the free tool that reads your CPU/motherboard temperatures).
- Little **info bubbles (?)** beside settings explain what each one does.

The app works by talking to the cooler over USB (device `1044:7A4D`). Its window is a small web page that only your own PC can reach (`127.0.0.1`), shown in an app-style Edge/Chrome window. Nothing is sent to the internet, except downloads you start yourself (LibreHardwareMonitor setup).

<p align="center"><img width="1770" height="1170" alt="c75254ea-aa5d-48af-a359-52b750988fcc" src="https://github.com/user-attachments/assets/e39eefb3-6886-42a0-8161-65a9a9f960d3" />


<p align="center"><img width="1770" height="1170" alt="8711b253-8157-4f62-bca1-b2a9a7150690" src="https://github.com/user-attachments/assets/a6bfacfa-13b9-45bc-8f2c-1911dcc654c5" />


<p align="center"><img width="1770" height="1170" alt="d572d639-82fc-470f-82af-c23bc3fb3b80" src="https://github.com/user-attachments/assets/d057d7d9-611f-4249-bc45-111e346a1f53" />


<p align="center"><img width="1770" height="1170" alt="212e17fb-74f6-4d2e-bd03-6102d23cc2af" src="https://github.com/user-attachments/assets/a8061713-9660-423a-a936-49429f212f14" />


## Requirements
- Windows 10 or 11
- Microsoft Edge or Google Chrome (Edge is already on Windows)
- A Gigabyte AORUS WATERFORCE X 360 (LCD version)
- Close or uninstall Gigabyte Control Center first. Two programs can't control the screen at the same time.

## Install (easiest)

1. Go to the **Releases** page of this repository and download `WaterforceScreenControl.exe`.
2. Put it in a permanent folder, for example `C:\Tools\WaterforceScreenControl\`.
3. Double-click it. Windows SmartScreen may warn about an unknown publisher (see *Troubleshooting*).
4. In **Settings**, turn on **Start with Windows** if you want it to start by itself.

## Build it yourself

You need Windows and [Python 3.12](https://www.python.org/downloads/) (tick "Add python.exe to PATH" / install the `py` launcher).

1. Download or clone this repository into a folder.
2. Double-click **`build.bat`**. It installs what it needs and builds the program (a minute or two).
3. Your program is at `dist\WaterforceScreenControl.exe`.

Files: `aorus_lcd.py` (the cooler engine and command-line tool), `aorus_lcd_app.py` (the app), `aorus_ui.py` (the window's page), `wsc_logo.py` + `icon.ico` (logo), `build.bat`.

## Temperatures (LibreHardwareMonitor)

CPU and motherboard temperatures come from [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor). If the Dashboard says it isn't reachable, press **Install LibreHardwareMonitor**. Windows will ask for permission once (administrator). The app downloads LibreHardwareMonitor and the PawnIO driver straight from their official GitHub pages, and sets LibreHardwareMonitor to start at login. If it fails, press **Show details → Copy details** and include that in a bug report.

## Troubleshooting

- **Windows SmartScreen / antivirus warns about the file.** The exe is built with PyInstaller and isn't code-signed, which often triggers warnings. You can build it yourself (above) and read the source.
- **The screen doesn't respond.** Quit Gigabyte Control Center completely (including its tray icon), then restart this app.
- **Taskbar icon looks blurry.** Fixed in 1.2.1. If it persists, unpin and re-pin the shortcut.
- **Logs** are in `%APPDATA%\WaterforceScreenControl\` (`aorus_lcd.log`).

##Installing your own build (Requires Python 3.12)

https://github.com/user-attachments/assets/340dc1c0-955a-429e-804e-5d8eb8a76357

## Credits and licences

- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (MPL-2.0) and [PawnIO](https://github.com/namazso/PawnIO) are downloaded by the optional setup, not bundled.
- Bundled Python libraries: hidapi, Pillow, pystray, imageio-ffmpeg (which includes **ffmpeg**, LGPL/GPL, see ffmpeg.org/legal.html).

## Licence

MIT License

## Version history

- **1.2.1** Sharper taskbar, window and tray icon.
- **1.2** Reworked LibreHardwareMonitor installer; Dashboard install button only when needed; removed the Gigabyte service disabler.
- **1.1** °C/°F, info bubbles, text slant and rotation.
