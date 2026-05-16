@echo off
setlocal enabledelayedexpansion
title SsakSsak

:: bat 파일이 있는 폴더 기준으로 실행 (어디서 더블클릭해도 동작)
cd /d "%~dp0"

echo ================================================
echo  SsakSsak (싹싹번역) - AI Lecture Slide Translator
echo ================================================
echo.

:: ── zip 미해제 감지 ──────────────────────────────
if not exist "%~dp0app.py" (
    echo [ERROR] app.py not found. Please extract the zip file first.
    echo.
    echo  How to fix:
    echo   1. Right-click the zip file
    echo   2. Select "Extract All"
    echo   3. Run run.bat from the extracted folder
    echo.
    goto :error
)

:: ── 1. Python 확인 ──────────────────────────────
echo [1/4] Checking Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install Python 3.10 or higher and run again.
    echo Download: https://www.python.org/downloads/
    goto :error
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python !PY_VER! detected
echo.

:: ── 2. Ollama 확인 및 설치 ──────────────────────
echo [2/4] Checking Ollama...
where ollama > nul 2>&1
if errorlevel 1 (
    echo Ollama not found. Starting auto-install...
    echo.
    set "INSTALLER=!TEMP!\ollama-setup.exe"
    echo Downloading Ollama installer...
    curl -L -o "!INSTALLER!" "https://ollama.com/download/OllamaSetup.exe"
    if errorlevel 1 (
        echo [ERROR] Download failed. Please check your internet connection.
        goto :error
    )
    echo Installing Ollama... (please wait)
    "!INSTALLER!" /silent
    timeout /t 15 > nul
    del "!INSTALLER!" 2>nul

    :: 설치 후 PATH 새로고침
    for /f "tokens=*" %%p in ('powershell -NoProfile -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\")"') do set "PATH=%%p;!PATH!"

    where ollama > nul 2>&1
    if errorlevel 1 (
        echo.
        echo [ERROR] Ollama installed but not recognized yet.
        echo Please close this window and run run.bat again.
        goto :error
    )
    echo [OK] Ollama installed successfully
) else (
    echo [OK] Ollama already installed
)
echo.

:: ── 3. AI 모델 다운로드 ──────────────────────
echo [3/4] Checking AI model...
echo   - llama3.2:3b (approx. 2.0GB)
echo.

ollama list 2>nul | findstr /i "llama3.2:3b" > nul
if errorlevel 1 (
    echo Downloading llama3.2:3b...
    ollama pull llama3.2:3b
    if errorlevel 1 (
        echo [ERROR] Failed to download llama3.2:3b.
        goto :error
    )
    echo [OK] llama3.2:3b ready
) else (
    echo [OK] llama3.2:3b already installed
)
echo.

:: ── 4. Python 패키지 설치 ───────────────────────
echo [4/4] Installing Python packages...
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    goto :error
)
echo [OK] Packages ready
echo.

:: ── 앱 실행 ────────────────────────────────────
echo ================================================
echo  Ready! Starting SsakSsak (싹싹번역)...
echo  Close the app window to stop.
echo ================================================
echo.

timeout /t 2 > nul
python "%~dp0desktop_run.py"
goto :end

:error
echo.
echo ================================================
echo  Setup failed. See error message above.
echo ================================================
echo.
pause
exit /b 1

:end
pause
