import sys
import os
import json
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


# ── 설정 파일 (최초 설치 여부 저장) ─────────────────
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ssaksak")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

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


# ── 경로 유틸 ────────────────────────────────────
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ── 최초 설치용 진행 창 (thread-safe) ────────────────
class SetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("싹싹번역 시작 중...")
        self.root.geometry("420x160")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        tk.Label(self.root, text="싹싹번역 준비 중입니다...",
                 font=("맑은 고딕", 11, "bold")).pack(pady=(20, 8))
        self.label = tk.Label(self.root, text="초기화 중...", font=("맑은 고딕", 9))
        self.label.pack()
        self.bar = ttk.Progressbar(self.root, length=360, mode='indeterminate')
        self.bar.pack(pady=10)
        self.bar.start(10)

    def update(self, msg):
        # 백그라운드 스레드에서 안전하게 UI 업데이트
        self.root.after(0, lambda: self.label.config(text=msg))

    def close(self):
        self.root.after(0, self.root.quit)


# ── 재실행 시 간단한 로딩 창 (thread-safe) ────────────
class LoadingWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("싹싹번역")
        self.root.geometry("300x80")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.label = tk.Label(self.root, text="싹싹번역 시작 중...", font=("맑은 고딕", 10))
        self.label.pack(pady=(16, 4))
        self.bar = ttk.Progressbar(self.root, length=260, mode='indeterminate')
        self.bar.pack()
        self.bar.start(10)

    def update(self, msg):
        self.root.after(0, lambda: self.label.config(text=msg))

    def close(self):
        self.root.after(0, self.root.quit)


# ── Ollama 실행 파일 탐색 (PATH + 일반 설치 경로) ──
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


# ── Ollama 확인 및 설치 ───────────────────────────
def ensure_ollama(win):
    win.update("Ollama 확인 중...")
    if find_ollama_exe():
        win.update("[OK] Ollama 이미 설치됨")
        return True

    win.update("Ollama 다운로드 중... (잠시 기다려주세요)")
    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")
    try:
        urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
        win.update("Ollama 설치 중...")
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
            win.update("[OK] Ollama 설치 완료")
            return True
        else:
            win.root.after(0, lambda: messagebox.showerror(
                "오류", "Ollama 설치 후 인식 실패.\n창을 닫고 싹싹번역.exe를 다시 실행해주세요."))
            return False
    except Exception as e:
        result = [False]
        event = threading.Event()

        def ask():
            result[0] = messagebox.askyesno(
                "Ollama 설치 오류",
                f"Ollama 자동 설치에 실패했습니다.\n({e})\n\n"
                "https://ollama.com 에서 직접 설치하셨나요?\n"
                "'예'를 누르면 앱을 계속 실행합니다."
            )
            event.set()

        win.root.after(0, ask)
        event.wait()

        if result[0]:
            if find_ollama_exe():
                win.update("[OK] Ollama 수동 설치 확인됨")
                return True
            win.root.after(0, lambda: messagebox.showerror(
                "오류", "Ollama를 찾을 수 없습니다.\n설치 후 다시 실행해주세요."))
        return False


# ── 모델 확인 및 다운로드 ──────────────────────────
def ensure_models(win):
    preload = ["qwen2.5:3b", "llama3.2:3b"]
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        installed = result.stdout
    except Exception:
        win.root.after(0, lambda: messagebox.showerror(
            "오류", "Ollama 실행 실패. Ollama가 정상 설치됐는지 확인해주세요."))
        return False

    for model in preload:
        if model not in installed:
            win.update(f"{model} 다운로드 중... (최초 1회, 약 2GB)")
            subprocess.run(["ollama", "pull", model])
        else:
            win.update(f"[OK] {model} 이미 설치됨")
        time.sleep(0.3)
    return True


# ── 모델 설치 여부 빠른 확인 ──────────────────────
def check_all_ready():
    if not find_ollama_exe():
        return False
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        installed = result.stdout
        return all(m in installed for m in ["qwen2.5:3b", "llama3.2:3b"])
    except Exception:
        return False


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
    config = load_config()
    all_ready = config.get("setup_complete") and check_all_ready()

    win = LoadingWindow() if all_ready else SetupWindow()

    # 결과 공유 변수
    exit_info = {"code": 0, "msg": ""}
    port_ref = [None]

    # ── 모든 무거운 작업은 백그라운드 스레드에서 ──
    def background_work():
        # 1. 설치 확인 (최초 실행 시만)
        if not all_ready:
            if not ensure_ollama(win):
                exit_info["code"] = 1
                win.close()
                return
            if not ensure_models(win):
                exit_info["code"] = 1
                win.close()
                return
            config["setup_complete"] = True
            save_config(config)

        # 2. Streamlit 서버 시작
        win.update("앱 서버 시작 중...")
        port = find_free_port()
        port_ref[0] = port

        t = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
        t.start()

        # 3. 서버 응답 대기
        if not wait_for_server(port, timeout=30):
            exit_info["code"] = 2
            exit_info["msg"] = "서버 시작 실패. 다시 실행해주세요."
            win.close()
            return

        # 4. 준비 완료 → 로딩창 닫기
        win.close()

    t_bg = threading.Thread(target=background_work, daemon=True)
    t_bg.start()

    # 메인 스레드: GUI 이벤트 루프 (응답 없음 방지)
    win.root.mainloop()
    win.root.destroy()

    # 오류 처리
    if exit_info["code"] != 0:
        if exit_info["msg"]:
            messagebox.showerror("오류", exit_info["msg"])
        sys.exit(1)

    # 5. 브라우저로 열기
    import webbrowser
    webbrowser.open(f"http://localhost:{port_ref[0]}")

    # 6. 앱 제어창 (닫으면 종료)
    root = tk.Tk()
    root.title("싹싹번역")
    root.geometry("320x130")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    tk.Label(root, text="🎓 싹싹번역 실행 중",
             font=("맑은 고딕", 12, "bold")).pack(pady=(18, 4))
    tk.Label(root, text="브라우저에서 앱이 열려 있습니다.\n이 창을 닫으면 앱이 종료됩니다.",
             font=("맑은 고딕", 9), fg="#555").pack()
    tk.Button(root, text="앱 종료", command=root.destroy,
              bg="#e74c3c", fg="white", font=("맑은 고딕", 9),
              relief="flat", padx=16, pady=4).pack(pady=10)

    root.mainloop()
