@echo off
echo Building 싹싹번역.exe...

pip install pyinstaller > nul

pyinstaller --noconfirm --onefile --windowed ^
  --name "싹싹번역" ^
  --icon "icon.ico" ^
  --add-data "app.py;." ^
  --add-data "glossary.py;." ^
  --collect-all streamlit ^
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
echo Build complete! Output: dist\싹싹번역\싹싹번역.exe
pause
