# Simple-PDF-Player
Status: Alpha; Working on it.

### Description
Its a WinAmp style player of PDFs, using, Kokoro for TTS and NiceGUI for GUI.

### Features
- Continuous play, without gaps in audio.
- Program now may launch without terminal.
- Button bar with tool tips.
- File label detail, fitted window size.
- Persistent settings via Json.
- Popup configuration box.

### Preview
![Image Missing](https://raw.githubusercontent.com/wiseman-timelord/Simple-PDF-Player/refs/heads/main/media/simple-pdf-player.jpg)

### Structure
```
.\Simple-PDF-Player.bat
.\installer.py
.\launcher.py
.\scripts\__init__.py
.\scripts\displays.py
.\scripts\speach.py
.\scripts\temporary.py
.\scripts\utility.py
```

### Requirements
- Python 3.11-3.12 - Kimi assessed the v0.05 scripts to find this out.
- Windows 10 tested - It may also work on windows 8.1/11.
- Sound Device - It will make noises on Default device.
- Pdf to play - A Pdf made by testing PDF creation site is provided in `.\data`.

### Instructions
```
1. Copy latest release to some suitable folder, and unpack.
2. Run the batch via right click run as admin.
3. it will present a menu, select 2 to install (ensure to allow through firewall).
4. After installing it will return to the menu, press 1 to run the program.
5. In the program click to open a file, select file, then click play button.
6. After a short while the audio will begin, you may pause/stop etc while playing.
7. Shutting down is as per normal, click the [X] on the right of the bar.
```

### Notation
- You may create a shortcut for the batch on your taskbar by using in the target box of the shortcut, for example `cmd /c "c:\full\path\to\batch\Simple-Pdf-Player.bat", then change shortcut icon, then dragging that onto the taskbar.

### Development
- Further development possible, TBA.
