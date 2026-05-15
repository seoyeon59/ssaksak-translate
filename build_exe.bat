@echo off
echo Building EduTrans.exe...

pip install pyinstaller pywebview > nul

pyinstaller --noconfirm --onedir --windowed ^
  --name "ssackssack-translate" ^
  --icon "icon.ico" ^
  --add-data "app.py;." ^
  --add-data "glossary.py;." ^
  --add-data "fonts;fonts" ^
  --collect-all streamlit ^
  --collect-all pywebview ^
  --hidden-import streamlit.web.cli ^
  --hidden-import streamlit.runtime.scriptrunner ^
  desktop_run.py

echo.
echo Build complete! Output: dist\EduTrans\EduTrans.exe
pause
