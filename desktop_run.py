import sys
import os
import json
import threading
import time
import subprocess
import urllib.request


# ── Streamlit signal 핸들러 패치 ──────────────────
def _patch_streamlit_signal():
    try:
        import streamlit.web.bootstrap as _bootstrap
        _bootstrap._set_up_signal_handler = lambda server: None
    except Exception:
        pass

_patch_streamlit_signal()


# ── 설정 파일 ─────────────────────────────────────
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ssaksak")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
STATUS_PATH = os.path.join(CONFIG_DIR, "setup_status.json")

def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)

def write_status(status, message, progress=0):
    """설치 진행 상태를 파일에 저장 → Streamlit이 읽어 표시"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({"status": status, "message": message, "progress": progress}, f)
    except Exception:
        pass


# ── 경로 유틸 ─────────────────────────────────────
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ── Ollama 탐색 ───────────────────────────────────
def find_ollama_exe():
    import shutil
    if shutil.which("ollama"):
        return True
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama"),
        os.path.join(os.environ.get("APPDATA", ""), "Programs", "Ollama"),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "Ollama"),
        r"C:\Program Files\Ollama",
        r"C:\Program Files (x86)\Ollama",
    ]
    for folder in candidates:
        if os.path.exists(os.path.join(folder, "ollama.exe")):
            os.environ["PATH"] = folder + ";" + os.environ.get("PATH", "")
            return True
    return False


# ── Ollama 설치 (브라우저에 상태 표시) ───────────────
def ensure_ollama_bg():
    write_status("installing", "Ollama 확인 중...", 5)
    if find_ollama_exe():
        write_status("installing", "Ollama 확인 완료", 20)
        return True

    write_status("installing", "Ollama 다운로드 중... (잠시 기다려주세요)", 10)
    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")
    try:
        urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
        write_status("installing", "Ollama 설치 중...", 15)
        subprocess.run([installer_path, "/silent"], check=True)
        time.sleep(10)
        try:
            os.remove(installer_path)
        except Exception:
            pass

        try:
            new_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
                capture_output=True, text=True
            ).stdout.strip()
            os.environ["PATH"] = new_path + ";" + os.environ.get("PATH", "")
        except Exception:
            pass

        if find_ollama_exe():
            write_status("installing", "Ollama 설치 완료", 20)
            return True
        else:
            write_status("error",
                "Ollama 설치 후 인식에 실패했습니다.\n"
                "앱을 닫고 다시 실행해주세요.")
            return False
    except Exception as e:
        write_status("error",
            f"Ollama 자동 설치에 실패했습니다.\n\n"
            f"👉 https://ollama.com 에서 직접 설치 후 앱을 재실행해주세요.\n\n"
            f"(오류: {e})")
        return False


# ── 모델 확인 및 다운로드 ─────────────────────────
def ensure_models_bg():
    preload = ["qwen2.5:3b", "llama3.2:3b"]
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        installed = result.stdout
    except Exception:
        write_status("error", "Ollama 실행에 실패했습니다.\nOllama가 정상 설치됐는지 확인해주세요.")
        return False

    total = len(preload)
    for idx, model in enumerate(preload):
        base_progress = 30 + int((idx / total) * 60)
        if model not in installed:
            write_status("installing",
                f"{model} 다운로드 중...\n(최초 1회, 약 2GB — 인터넷 속도에 따라 10~20분 소요)",
                base_progress)
            subprocess.run(["ollama", "pull", model])
        else:
            write_status("installing", f"✅ {model} 확인 완료", base_progress + int(60 / total))
        time.sleep(0.3)
    return True


# ── 빠른 준비 확인 ────────────────────────────────
def check_all_ready():
    if not find_ollama_exe():
        return False
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        installed = result.stdout
        return all(m in installed for m in ["qwen2.5:3b", "llama3.2:3b"])
    except Exception:
        return False


# ── 백그라운드 설치 작업 ──────────────────────────
def background_setup():
    config = load_config()
    if config.get("setup_complete") and check_all_ready():
        write_status("ready", "준비 완료", 100)
        return

    if not ensure_ollama_bg():
        return
    if not ensure_models_bg():
        return

    config["setup_complete"] = True
    save_config(config)
    write_status("ready", "설치 완료", 100)


# ── Streamlit 실행 ────────────────────────────────
def run_streamlit(port):
    app_path = resource_path('app.py')

    if getattr(sys, 'frozen', False):
        static_path = resource_path(os.path.join('streamlit', 'static'))
        os.environ['STREAMLIT_STATIC_PATH'] = static_path

    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.port={port}",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.fileWatcherType=none",
    ]
    from streamlit.web import cli as stcli
    stcli.main()


def find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def wait_for_server(port, timeout=30):
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(f"http://localhost:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


# ── 메인 ─────────────────────────────────────────
if __name__ == "__main__":
    config = load_config()
    all_ready = config.get("setup_complete") and check_all_ready()

    # 초기 상태 설정
    if all_ready:
        write_status("ready", "준비 완료", 100)
    else:
        write_status("installing", "초기화 중...", 0)

    # 설치 작업 백그라운드 실행
    t_setup = threading.Thread(target=background_setup, daemon=True)
    t_setup.start()

    # Streamlit 서버 시작
    port = find_free_port()
    t_st = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
    t_st.start()

    # 서버 준비 대기
    wait_for_server(port, timeout=30)

    # 브라우저 열기
    import webbrowser
    webbrowser.open(f"http://localhost:{port}")

    # 프로세스 유지 (창 없이 백그라운드 실행)
    try:
        while t_st.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
