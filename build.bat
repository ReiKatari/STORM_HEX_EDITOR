@echo off
echo Building STORM HEX EDITOR...
pyinstaller --noconfirm --onefile --windowed --noupx --icon "stormhexeditor.ico" --add-data "stormhexeditor.ico;." --name "STORM HEX EDITOR" "stormhexeditor.py"
echo Build Complete!
pause
