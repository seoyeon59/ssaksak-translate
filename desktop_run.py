import sys
import os
import threading
import time
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox


# ── Streamlit signal 핸들러 패치 (백그라운드 스레드 실행 대응) ──
def _patch_streamlit_signal():
    try:
        import streamlit.web.bootstrap as _bootstrap
        _bootstrap._set_up_signal_handler = lambda server: None
    except Exception:
        pass

_patch_streamlit_signal()


# ── 경로 유틸 ────────────────────────────────────
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ── 진행 상황 팝업 창 ─────────────────────────────
class SetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EduTrans 시작 중...")
        self.root.geometry("420x160")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        tk.Label(self.root, text="EduTrans 준비 중입니다...",
                 font=("맑은 고딕", 11, "bold")).pack(pady=(20, 8))
        self.label = tk.Label(self.root, text="초기화 중...", font=("맑은 고딕", 9))
        self.label.pack()
        self.bar = ttk.Progressbar(self.root, length=360, mode='indeterminate')
        self.bar.pack(pady=10)
        self.bar.start(10)
        self.root.update()

    def update(self, msg):
        self.label.config(text=msg)
        self.root.update()

    def close(self):
        self.bar.stop()
        self.root.destroy()


# ── Ollama 확인 및 설치 ───────────────────────────
def ensure_ollama(win):
    import shutil
    win.update("Ollama 확인 중...")
    if shutil.which("ollama"):
        win.update("[OK] Ollama 이미 설치됨")
        return True

    win.update("Ollama 다운로드 중... (잠시 기다려주세요)")
    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")
    try:
        urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
        win.update("Ollama 설치 중...")
        subprocess.run([installer_path, "/silent"], check=True)
        time.sleep(10)
        os.remove(installer_path)

        new_path = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
            capture_output=True, text=True
        ).stdout.strip()
        os.environ["PATH"] = new_path + ";" + os.environ.get("PATH", "")

        if shutil.which("ollama"):
            win.update("[OK] Ollama 설치 완료")
            return True
        else:
            messagebox.showerror("오류", "Ollama 설치 후 인식 실패.\n창을 닫고 EduTrans.exe를 다시 실행해주세요.")
            return False
    except Exception as e:
        messagebox.showerror("오류", f"Ollama 설치 실패:\n{e}")
        return False


# ── 모델 확인 및 다운로드 ──────────────────────────
def ensure_models(win):
    preload = ["qwen2.5:3b", "llama3.2:3b"]
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        installed = result.stdout
    except Exception:
        messagebox.showerror("오류", "Ollama 실행 실패. Ollama가 정상 설치됐는지 확인해주세요.")
        return False

    for model in preload:
        if model not in installed:
            win.update(f"{model} 다운로드 중... (최초 1회, 약 2GB)")
            subprocess.run(["ollama", "pull", model])
        else:
            win.update(f"[OK] {model} 이미 설치됨")
        time.sleep(0.3)
    return True


# ── Streamlit 백그라운드 실행 ─────────────────────
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
    # 1. 설치 팝업
    win = SetupWindow()

    if not ensure_ollama(win):
        win.close()
        sys.exit(1)

    if not ensure_models(win):
        win.close()
        sys.exit(1)

    win.update("앱 서버 시작 중...")

    # 2. 빈 포트 찾기
    port = find_free_port()

    # 3. Streamlit을 백그라운드 스레드에서 실행 (signal 패치로 오류 방지)
    t = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
    t.start()

    # 4. 서버 응답 대기
    if not wait_for_server(port, timeout=30):
        win.close()
        messagebox.showerror("오류", "서버 시작 실패. 다시 실행해주세요.")
        sys.exit(1)

    win.close()  # 팝업 닫기

    # 5. pywebview로 데스크탑 창 열기 (메인 스레드)
    import webview
    webview.create_window(
        "EduTrans - 강의자료 번역기",
        f"http://localhost:{port}",
        width=1280,
        height=860,
        resizable=True,
    )
    webview.start()
