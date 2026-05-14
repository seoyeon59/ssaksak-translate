@echo off
echo Building EduTrans.exe...

pip install pyinstaller pywebview > nul

pyinstaller --noconfirm --onedir --windowed ^
  --name "EduTrans" ^
  --icon "icon.ico" ^
  --add-data "app.py;." ^
  --add-data "glossary.py;." ^
  --collect-all streamlit ^
  --collect-all pywebview ^
  --collect-all pymupdf ^
  --collect-all pptx ^
  --collect-all langchain_ollama ^
  --hidden-import fitz ^
  --hidden-import pptx ^
  --hidden-import pptx.util ^
  --hidden-import pptx.dml.color ^
  --hidden-import langchain_ollama ^
  --hidden-import streamlit.web.cli ^
  --hidden-import streamlit.runtime.scriptrunner ^
  desktop_run.py

echo.
echo Build complete! Output: dist\EduTrans\EduTrans.exe
pause
