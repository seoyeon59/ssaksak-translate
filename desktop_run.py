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
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({"status": status, "message": message, "progress": progress}, f)
    except Exception:
        pass


# ── subprocess 창 숨김 (Windows) ─────────────────
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


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


# ── Ollama 설치 ───────────────────────────────────
def ensure_ollama_bg(update_ui):
    update_ui(5, "Ollama 확인 중...")
    if find_ollama_exe():
        update_ui(20, "Ollama 확인 완료 ✅")
        return True

    update_ui(10, "Ollama 다운로드 중... (잠시 기다려주세요)")
    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")
    try:
        def _reporthook(block_count, block_size, total_size):
            if total_size > 0:
                downloaded = block_count * block_size
                pct = min(downloaded / total_size * 100, 100)
                mb_done = downloaded / 1024 / 1024
                mb_total = total_size / 1024 / 1024
                # 전체 progress 10~18% 구간에 매핑
                mapped = 10 + pct * 0.08
                update_ui(mapped, f"Ollama 다운로드 중... {mb_done:.0f} / {mb_total:.0f} MB ({pct:.0f}%)")

        urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path, _reporthook)
        update_ui(15, "Ollama 설치 중...")
        subprocess.run([installer_path, "/silent"], check=True, creationflags=_NO_WINDOW)
        time.sleep(10)
        try:
            os.remove(installer_path)
        except Exception:
            pass

        try:
            new_path = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
                capture_output=True, text=True, creationflags=_NO_WINDOW
            ).stdout.strip()
            os.environ["PATH"] = new_path + ";" + os.environ.get("PATH", "")
        except Exception:
            pass

        if find_ollama_exe():
            update_ui(20, "Ollama 설치 완료 ✅")
            return True
        else:
            update_ui(-1, "Ollama 설치 후 인식 실패\n앱을 닫고 다시 실행해주세요.")
            return False
    except Exception as e:
        update_ui(-1,
            f"Ollama 자동 설치 실패\n"
            f"https://ollama.com 에서 직접 설치 후 재실행해주세요.\n(오류: {e})")
        return False


# ── 모델 확인 및 다운로드 ─────────────────────────
def ensure_models_bg(update_ui):
    preload = ["qwen2.5:3b", "llama3.2:3b"]
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10, creationflags=_NO_WINDOW)
        installed = result.stdout
    except Exception:
        update_ui(-1, "Ollama 실행 실패\nOllama가 정상 설치됐는지 확인해주세요.")
        return False

    total = len(preload)
    for idx, model in enumerate(preload):
        # 이 모델이 차지하는 전체 progress 구간 (30~90%)
        seg_start = 30 + int((idx / total) * 60)
        seg_end   = 30 + int(((idx + 1) / total) * 60)

        if model not in installed:
            update_ui(seg_start,
                f"[{idx+1}/{total}] {model} 다운로드 준비 중...\n"
                f"(최초 1회, 약 2GB — 인터넷 속도에 따라 10~20분 소요)")

            proc = subprocess.Popen(
                ["ollama", "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_NO_WINDOW,
            )

            buf = ""
            for chunk in iter(lambda: proc.stdout.read(64), ""):
                buf += chunk
                # \r 또는 \n 기준으로 마지막 줄 추출
                lines = buf.replace("\r", "\n").split("\n")
                buf = lines[-1]
                last = ""
                for line in reversed(lines[:-1]):
                    if line.strip():
                        last = line.strip()
                        break
                if not last:
                    continue

                # "pulling xxxx...  45% ▕...▏  876 MB/1.9 GB  25 MB/s  41s" 파싱
                import re
                m = re.search(r"(\d+)%.*?([\d.]+\s*\w+)\s*/\s*([\d.]+\s*\w+)", last)
                if m:
                    pct = int(m.group(1))
                    done_str = m.group(2)
                    total_str = m.group(3)
                    mapped = seg_start + (pct / 100) * (seg_end - seg_start)
                    update_ui(mapped,
                        f"[{idx+1}/{total}] {model} 다운로드 중...\n"
                        f"{done_str} / {total_str}  ({pct}%)")
                elif "verifying" in last.lower():
                    update_ui(seg_end - 1, f"[{idx+1}/{total}] {model} 검증 중...")
                elif "writing" in last.lower() or "success" in last.lower():
                    update_ui(seg_end, f"[{idx+1}/{total}] {model} 설치 완료 ✅")

            proc.wait()
        else:
            update_ui(seg_end, f"[{idx+1}/{total}] {model} 확인 완료 ✅")

        time.sleep(0.3)
    return True


# ── 빠른 준비 확인 ────────────────────────────────
def check_all_ready():
    if not find_ollama_exe():
        return False
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW)
        installed = result.stdout
        return all(m in installed for m in ["qwen2.5:3b", "llama3.2:3b"])
    except Exception:
        return False


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


# ── 설치 진행 tkinter 창 ──────────────────────────
def run_setup_window(port_holder, done_event):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("싹싹번역 초기 설정")
    root.geometry("480x300")
    root.resizable(False, False)
    root.configure(bg="#f0f4ff")

    # 창 가운데 정렬
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - 480) // 2
    y = (sh - 300) // 2
    root.geometry(f"480x300+{x}+{y}")

    # 아이콘 설정 (있을 경우)
    try:
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # UI 요소
    tk.Label(root, text="⚙️  싹싹번역 초기 설정 중...",
             font=("맑은 고딕", 14, "bold"), bg="#f0f4ff", fg="#1e3a8a").pack(pady=(30, 6))

    tk.Label(root, text="최초 1회 설정입니다. 완료되면 자동으로 번역 앱이 열립니다.",
             font=("맑은 고딕", 9), bg="#f0f4ff", fg="#555").pack(pady=(0, 20))

    progress_var = tk.DoubleVar(value=0)
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("blue.Horizontal.TProgressbar",
                    troughcolor="#dde6f7", background="#3b82f6",
                    thickness=18)
    bar = ttk.Progressbar(root, variable=progress_var, maximum=100,
                          length=400, style="blue.Horizontal.TProgressbar")
    bar.pack(pady=(0, 12))

    msg_var = tk.StringVar(value="초기화 중...")
    msg_label = tk.Label(root, textvariable=msg_var,
                         font=("맑은 고딕", 9), bg="#f0f4ff", fg="#333",
                         wraplength=440, justify="center")
    msg_label.pack()

    note = tk.Label(root,
                    text="ℹ  이 창을 닫아도 설치는 계속 진행되지 않습니다.\n     창이 열려 있는 동안 설치가 진행됩니다.",
                    font=("맑은 고딕", 8), bg="#e8f0fe", fg="#3b4a6b",
                    justify="center", pady=6)
    note.pack(side="bottom", fill="x")

    # 상태 업데이트 함수 (스레드에서 호출)
    def update_ui(progress, message):
        write_status("installing" if progress >= 0 else "error", message, max(progress, 0))
        root.after(0, lambda: _apply(progress, message))

    def _apply(progress, message):
        if progress >= 0:
            progress_var.set(progress)
            msg_var.set(message)
        else:
            msg_var.set("❌ " + message)
            progress_var.set(0)

    # 설치 완료 시 창 닫고 브라우저 열기
    def on_done():
        write_status("ready", "준비 완료", 100)
        port = port_holder[0]
        if port:
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")
        root.destroy()

    def on_error():
        pass  # 창은 유지 (오류 메시지 보여줌)

    # 설치 작업 스레드
    def setup_thread():
        config = load_config()
        if config.get("setup_complete") and check_all_ready():
            write_status("ready", "준비 완료", 100)
            root.after(0, on_done)
            return

        if not ensure_ollama_bg(update_ui):
            root.after(0, on_error)
            return
        if not ensure_models_bg(update_ui):
            root.after(0, on_error)
            return

        config["setup_complete"] = True
        save_config(config)
        update_ui(100, "설치 완료! 번역 앱을 시작합니다...")
        time.sleep(1)
        root.after(0, on_done)

    threading.Thread(target=setup_thread, daemon=True).start()

    root.mainloop()
    done_event.set()


# ── 메인 ─────────────────────────────────────────
if __name__ == "__main__":
    config = load_config()
    all_ready = config.get("setup_complete") and check_all_ready()

    port = find_free_port()
    port_holder = [port]

    # Streamlit 서버 백그라운드 시작
    t_st = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
    t_st.start()

    done_event = threading.Event()

    if all_ready:
        # 설치 완료 상태 → 서버 준비되면 바로 브라우저 열기
        write_status("ready", "준비 완료", 100)
        wait_for_server(port, timeout=30)
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")
    else:
        # 미설치 → tkinter 설치 창 표시 (서버와 병렬 진행)
        threading.Thread(
            target=lambda: (wait_for_server(port, timeout=60)),
            daemon=True
        ).start()
        run_setup_window(port_holder, done_event)

    # 프로세스 유지
    try:
        while t_st.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
