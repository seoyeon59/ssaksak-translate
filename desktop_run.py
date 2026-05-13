import sys
import os
import threading
import time
import webbrowser
import subprocess
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox


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
        urllib.request.urlretrieve(
            "https://ollama.com/download/OllamaSetup.exe",
            installer_path
        )
        win.update("Ollama 설치 중...")
        subprocess.run([installer_path, "/silent"], check=True)
        time.sleep(10)
        os.remove(installer_path)

        # PATH 갱신 후 재확인
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
            messagebox.showerror("오류", "Ollama 설치 후 인식 실패.\n이 창을 닫고 EduTrans.exe를 다시 실행해주세요.")
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
        time.sleep(0.5)
    return True


# ── Streamlit 실행 ────────────────────────────────
def run_streamlit():
    app_path = resource_path('app.py')

    if getattr(sys, 'frozen', False):
        static_path = resource_path(os.path.join('streamlit', 'static'))
        os.environ['STREAMLIT_STATIC_PATH'] = static_path
        log_path = os.path.join(os.path.dirname(sys.executable), 'edutrans.log')
        sys.stdout = open(log_path, 'w', encoding='utf-8')
        sys.stderr = sys.stdout

    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.port=8501",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.fileWatcherType=none",
    ]
    from streamlit.web import cli as stcli
    stcli.main()


def wait_for_server(url, timeout=30):
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


# ── 메인 ─────────────────────────────────────────
if __name__ == "__main__":
    win = SetupWindow()

    # 1. Ollama 확인/설치
    if not ensure_ollama(win):
        win.close()
        sys.exit(1)

    # 2. 모델 확인/다운로드
    if not ensure_models(win):
        win.close()
        sys.exit(1)

    # 3. Streamlit 서버 시작
    win.update("앱 서버 시작 중...")
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    # 4. 서버 응답 대기
    if wait_for_server("http://localhost:8501", timeout=30):
        win.close()
        webbrowser.open("http://localhost:8501")
    else:
        win.close()
        log_path = os.path.join(os.path.dirname(sys.executable), 'edutrans.log')
        messagebox.showerror("오류", f"서버 시작 실패.\n로그 확인: {log_path}")
        sys.exit(1)

    t.join()
