@echo off
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconfirm --onefile --noconsole --name Dahaengi --icon icon.ico dahaengi.py
echo.
echo Done: dist\Dahaengi.exe
pause
