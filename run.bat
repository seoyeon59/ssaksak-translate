@echo off
chcp 65001 > nul
title EduTrans 설치 및 실행

echo ================================================
echo  EduTrans - AI 강의 슬라이드 번역기
echo ================================================
echo.

:: ── 1. Python 확인 ──────────────────────────────
echo [1/4] Python 확인 중...
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 설치하고 다시 실행해주세요.
    echo 다운로드: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% 감지됨
echo.

:: ── 2. Ollama 확인 및 설치 ──────────────────────
echo [2/4] Ollama 확인 중...
ollama --version > nul 2>&1
if errorlevel 1 (
    echo Ollama가 설치되어 있지 않습니다. 자동 설치를 시작합니다...
    echo.
    set OLLAMA_INSTALLER=%TEMP%\ollama-installer.exe
    echo 다운로드 중: https://ollama.com/download/OllamaSetup.exe
    curl -L -o "%OLLAMA_INSTALLER%" "https://ollama.com/download/OllamaSetup.exe"
    if errorlevel 1 (
        echo [오류] Ollama 다운로드 실패. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
    echo 설치 중...
    "%OLLAMA_INSTALLER%" /silent
    timeout /t 5 > nul
    del "%OLLAMA_INSTALLER%"
    ollama --version > nul 2>&1
    if errorlevel 1 (
        echo [오류] Ollama 설치 후에도 인식되지 않습니다.
        echo 수동으로 https://ollama.com 에서 설치해주세요.
        pause
        exit /b 1
    )
    echo [OK] Ollama 설치 완료
) else (
    for /f "tokens=*" %%v in ('ollama --version 2^>^&1') do echo [OK] %%v 감지됨
)
echo.

:: ── 3. 저사양 모델 확인 및 다운로드 ─────────────
echo [3/4] 기본 AI 모델 확인 중 (저사양 모델 미리 설치)...
echo  - qwen2.5:3b  (약 2.0GB)
echo  - llama3.2:3b (약 2.0GB)
echo.

ollama list 2>nul | findstr /i "qwen2.5:3b" > nul
if errorlevel 1 (
    echo [qwen2.5:3b] 다운로드 중...
    ollama pull qwen2.5:3b
    if errorlevel 1 (
        echo [오류] qwen2.5:3b 다운로드 실패. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
    echo [OK] qwen2.5:3b 완료
) else (
    echo [OK] qwen2.5:3b 이미 설치됨
)

ollama list 2>nul | findstr /i "llama3.2:3b" > nul
if errorlevel 1 (
    echo [llama3.2:3b] 다운로드 중...
    ollama pull llama3.2:3b
    if errorlevel 1 (
        echo [오류] llama3.2:3b 다운로드 실패. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )
    echo [OK] llama3.2:3b 완료
) else (
    echo [OK] llama3.2:3b 이미 설치됨
)

echo.
echo  * 고사양 모델 (llama3) 은 앱에서 선택 시 자동으로 다운로드됩니다.
echo.

:: ── 4. Python 패키지 설치 ───────────────────────
echo [4/4] Python 패키지 확인 중...
pip show streamlit > nul 2>&1
if errorlevel 1 (
    echo 패키지를 설치합니다...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 패키지 설치 실패.