@echo off
echo Building SsakSsak.exe...

pip install pyinstaller pywebview > nul

REM fonts 폴더가 없으면 빈 폴더라도 만들어 PyInstaller 경고 회피
if not exist "fonts" mkdir fonts

pyinstaller --noconfirm --onedir --windowed ^
  --name "SsakSsak" ^
  --icon "icon.ico" ^
  --add-data "app.py;." ^
  --add-data "glossary.py;." ^
  --add-data "fonts;fonts" ^
  --collect-all streamlit ^
  --collect-all pywebview ^
  --hidden-import streamlit.web.cli ^
  --hidden-import streamlit.runtime.scriptrunner ^
  --hidden-import multiprocessing ^
  desktop_run.py

echo.
echo Build complete! Output: dist\SsakSsak\SsakSsak.exe
echo.
echo Next steps:
echo   1) ZIP 배포: dist\SsakSsak\ 폴더를 통째로 압축해서 GitHub Release에 업로드
echo   2) 설치 마법사: Inno Setup으로 installer.iss 컴파일 → SsakSsak-Setup.exe 생성
pause
