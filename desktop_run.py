import sys
import os
import re
import threading
import time
import subprocess
import urllib.request
import socket
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

# Windows 전용 플래그
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


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
        self.root.geometry("480x210")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        tk.Label(self.root, text="EduTrans 준비 중입니다...",
                 font=("맑은 고딕", 11, "bold")).pack(pady=(16, 4))

        self.label = tk.Label(self.root, text="초기화 중...", font=("맑은 고딕", 9))
        self.label.pack()

        # 세부 진행 정보 (다운로드 속도, 용량 등)
        self.detail = tk.Label(self.root, text="", font=("맑은 고딕", 8), fg="#555555")
        self.detail.pack(pady=(2, 0))

        self._mode = 'indeterminate'
        self.bar = ttk.Progressbar(self.root, length=430, mode='indeterminate')
        self.bar.pack(pady=10)
        self.bar.start(10)
        self.root.update()

    def update(self, msg, detail=""):
        self.label.config(text=msg)
        self.detail.config(text=detail)
        self.root.update()

    def set_progress(self, value, maximum=100):
        """determinate 모드로 전환 후 진행률 설정 (0~100)"""
        if self._mode != 'determinate':
            self.bar.stop()
            self.bar.config(mode='determinate', maximum=maximum)
            self._mode = 'determinate'
        self.bar['value'] = value
        self.root.update()

    def set_indeterminate(self):
        """다시 indeterminate(애니메이션) 모드로"""
        if self._mode != 'indeterminate':
            self.bar.config(mode='indeterminate')
            self.bar.start(10)
            self._mode = 'indeterminate'
        self.root.update()

    def close(self):
        self.bar.stop()
        self.root.destroy()


# ── Ollama 설치 확인 및 자동 설치 ───────────────────
def ensure_ollama(win):
    import shutil
    win.update("Ollama 확인 중...", "설치 여부 검사")

    if shutil.which("ollama"):
        win.update("[OK] Ollama 이미 설치됨", "")
        return True

    win.update("Ollama 다운로드 중...", "약 80MB, 잠시 기다려주세요")
    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")

    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                downloaded = count * block_size
                pct = min(int(downloaded * 100 / total_size), 100)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                win.set_progress(pct)
                win.update(
                    f"Ollama 다운로드 중... ({pct}%)",
                    f"{mb_done:.1f} MB / {mb_total:.1f} MB"
                )

        urllib.request.urlretrieve(
            "https://ollama.com/download/OllamaSetup.exe",
            installer_path,
            reporthook=reporthook
        )

        win.set_indeterminate()
        win.update("Ollama 설치 중...", "10~30초 소요됩니다")
        subprocess.run([installer_path, "/silent"], check=True)
        time.sleep(8)
        try:
            os.remove(installer_path)
        except Exception:
            pass

        # 설치 후 PATH 갱신
        new_path = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[System.Environment]::GetEnvironmentVariable('PATH','Machine')"],
            capture_output=True, text=True
        ).stdout.strip()
        os.environ["PATH"] = new_path + ";" + os.environ.get("PATH", "")

        if not shutil.which("ollama"):
            messagebox.showerror("오류",
                "Ollama 설치 후 인식 실패.\n창을 닫고 EduTrans.exe를 다시 실행해주세요.")
            return False

        win.update("[OK] Ollama 설치 완료", "")
        return True

    except Exception as e:
        messagebox.showerror("오류", f"Ollama 설치 실패:\n{e}")
        return False


# ── Ollama 서비스 실행 확인 및 자동 시작 ─────────────
def is_ollama_up():
    """Ollama API(11434포트)가 응답하는지 확인"""
    try:
        with socket.create_connection(("localhost", 11434), timeout=1):
            return True
    except Exception:
        return False


def ensure_ollama_running(win):
    """Ollama 서비스가 꺼져 있으면 자동으로 시작하고 응답 대기"""
    if is_ollama_up():
        win.update("[OK] Ollama 서비스 실행 중", "")
        return True

    win.update("Ollama 서비스 시작 중...", "잠시 기다려주세요")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )

    for i in range(30):
        time.sleep(1)
        if is_ollama_up():
            win.update("[OK] Ollama 서비스 시작 완료", "")
            return True
        win.update("Ollama 서비스 시작 중...", f"응답 대기 중... ({i + 1}/30초)")

    messagebox.showerror("오류",
        "Ollama 서비스가 30초 내에 시작되지 않았습니다.\n"
        "'ollama serve' 명령을 직접 실행한 뒤 EduTrans를 다시 시작해주세요.")
    return False


# ── 모델 다운로드 (세부 진행 표시) ──────────────────
def pull_model_with_progress(win, model):
    """ollama pull 실행 + stdout 파싱으로 실시간 진행률 표시"""
    win.set_indeterminate()
    win.update(f"{model} 다운로드 준비 중...", "manifest 확인 중")

    proc = subprocess.Popen(
        ["ollama", "pull", model],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue

        # 진행률 파싱: "pulling abc123... 45% ▕...▏ 1.2 GB/2.7 GB  50 MB/s  30s"
        pct_match  = re.search(r'(\d+)%', line)
        size_match = re.search(r'([\d.]+)\s*(GB|MB|KB)\s*/\s*([\d.]+)\s*(GB|MB|KB)', line)
        speed_match = re.search(r'([\d.]+\s*(?:GB|MB|KB)/s)', line)
        eta_match  = re.search(r'(\d+[smh](?:\s*\d+[smh])*)', line)

        detail_parts = []
        if size_match:
            d, du = float(size_match.group(1)), size_match.group(2)
            t, tu = float(size_match.group(3)), size_match.group(4)
            detail_parts.append(f"{d:.1f} {du} / {t:.1f} {tu}")
        if speed_match:
            detail_parts.append(speed_match.group(1))
        if eta_match and "%" in line:
            detail_parts.append(f"남은 시간: {eta_match.group(1)}")

        detail_text = "  |  ".join(detail_parts) if detail_parts else line[:70]

        if pct_match:
            pct = int(pct_match.group(1))
            win.set_progress(pct)
            win.update(f"{model} 다운로드 중... ({pct}%)", detail_text)
        elif "pulling manifest" in line:
            win.set_indeterminate()
            win.update(f"{model} 다운로드 준비 중...", "서버에서 정보를 가져오는 중")
        elif "verifying" in line:
            win.set_indeterminate()
            win.update(f"{model} 검증 중...", "다운로드 무결성 확인")
        elif "writing manifest" in line or "success" in line:
            win.set_indeterminate()
            win.update(f"{model} 마무리 중...", "")
        else:
            win.update(f"{model} 다운로드 중...", line[:70])

    proc.wait()
    win.set_indeterminate()
    return proc.returncode == 0


# ── 모델 사전 설치 확인 ───────────────────────────
def ensure_models(win):
    preload = ["qwen2.5:3b", "llama3.2:3b"]
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        installed = result.stdout
    except Exception:
        messagebox.showerror("오류", "Ollama 실행 실패. Ollama가 정상 설치됐는지 확인해주세요.")
        return False

    for model in preload:
        if model not in installed:
            ok = pull_model_with_progress(win, model)
            if not ok:
                messagebox.showerror("오류",
                    f"{model} 다운로드에 실패했습니다.\n인터넷 연결을 확인하고 다시 시도해주세요.")
                return False
            win.update(f"[OK] {model} 다운로드 완료", "")
        else:
            win.update(f"[OK] {model} 이미 설치됨", "")
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
    win = SetupWindow()

    # 1. Ollama 설치 확인
    if not ensure_ollama(win):
        win.close()
        sys.exit(1)

    # 2. Ollama 서비스 실행 확인 (핵심: 새 노트북 응답 오류 방지)
    if not ensure_ollama_running(win):
        win.close()
        sys.exit(1)

    # 3. 모델 사전 설치 (qwen2.5:3b, llama3.2:3b)
    if not ensure_models(win):
        win.close()
        sys.exit(1)

    win.update("앱 서버 시작 중...", "Streamlit 초기화")

    # 4. 빈 포트 찾기
    port = find_free_port()

    # 5. Streamlit을 백그라운드 스레드에서 실행
    t = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
    t.start()

    # 6. 서버 응답 대기
    if not wait_for_server(port, timeout=30):
        win.close()
        messagebox.showerror("오류", "서버 시작 실패. 다시 실행해주세요.")
        sys.exit(1)

    win.close()

    # 7. pywebview로 데스크탑 창 열기 (메인 스레드)
    import webview
    webview.create_window(
        "EduTrans - 강의자료 번역기",
        f"http://localhost:{port}",
        width=1280,
        height=860,
        resizable=True,
    )
    webview.start()
