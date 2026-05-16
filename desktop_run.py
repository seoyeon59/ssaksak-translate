import sys
import os
import re
import time
import atexit
import secrets
import shutil
import socket
import subprocess
import urllib.request
import urllib.error
import multiprocessing as mp
import platform
import tkinter as tk
from tkinter import ttk, messagebox

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes


# ── Streamlit signal 핸들러 패치 (multiprocessing 자식에서도 안전) ──
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


# ── 설정 ─────────────────────────────────────────
OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_DOWNLOAD_PAGE = "https://ollama.com/download"
NETWORK_TIMEOUT = 30          # 단일 read/connect 타임아웃 (초)
NETWORK_RETRIES = 3           # 다운로드/풀 재시도 횟수
MODEL_PULL_HARD_TIMEOUT = 60 * 60  # 모델 1개당 최대 1시간


# ── 시작 시 잔재 파일 청소 (#2 해결방안 3) ──────────
def cleanup_old_artifacts(days=7):
    """%TEMP%의 ollama-setup* 잔재를 즉시 삭제(파일 잠금 시 무시)."""
    temp_dir = os.environ.get("TEMP")
    if not temp_dir or not os.path.isdir(temp_dir):
        return
    for fname in os.listdir(temp_dir):
        if fname.lower().startswith("ollama-setup"):
            try:
                os.remove(os.path.join(temp_dir, fname))
            except OSError:
                pass


# ── 진행 상황 팝업 창 ─────────────────────────────
class SetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("싹싹번역 시작 중...")
        self.root.geometry("460x180")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        tk.Label(self.root, text="싹싹번역 준비 중입니다...",
                 font=("맑은 고딕", 11, "bold")).pack(pady=(20, 8))
        self.label = tk.Label(self.root, text="초기화 중...", font=("맑은 고딕", 9))
        self.label.pack()
        self.bar = ttk.Progressbar(self.root, length=400, mode='indeterminate')
        self.bar.pack(pady=10)
        self.bar.start(10)
        self._mode = 'indeterminate'
        self.root.update()

    def update(self, msg, percent=None):
        self.label.config(text=msg)
        if percent is None:
            if self._mode != 'indeterminate':
                self.bar.stop()
                self.bar.config(mode='indeterminate', maximum=100)
                self.bar.start(10)
                self._mode = 'indeterminate'
        else:
            if self._mode != 'determinate':
                self.bar.stop()
                self.bar.config(mode='determinate', maximum=100)
                self._mode = 'determinate'
            self.bar['value'] = max(0, min(100, percent))
        self.root.update()

    def close(self):
        try:
            self.bar.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


# ── 네트워크: 타임아웃 + 재시도 + 이어받기 + 진행률 (#8 해결방안 1+2+3) ──
def download_with_resume(url, dest_path, win=None, label_prefix=""):
    """Range 헤더로 이어받기 가능한 다운로더. 재시도/타임아웃/실시간 진행률 지원."""
    last_err = None
    for attempt in range(1, NETWORK_RETRIES + 1):
        try:
            existing = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
            req = urllib.request.Request(url)
            if existing > 0:
                req.add_header("Range", f"bytes={existing}-")
            with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT) as resp:
                # 서버가 Range 요청을 수락(206)했는지 확인
                resumed = (resp.status == 206 and existing > 0)
                content_length = resp.getheader("Content-Length")
                total = (existing if resumed else 0) + (int(content_length) if content_length else 0)

                mode = "ab" if resumed else "wb"
                if not resumed:
                    existing = 0
                downloaded = existing

                last_pct = -1
                with open(dest_path, mode) as f:
                    while True:
                        buf = resp.read(64 * 1024)
                        if not buf:
                            break
                        f.write(buf)
                        downloaded += len(buf)
                        if win and total > 0:
                            pct = downloaded * 100.0 / total
                            if int(pct) != last_pct:
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total / (1024 * 1024)
                                win.update(
                                    f"{label_prefix} {mb_done:.1f}/{mb_total:.1f} MB ({pct:.0f}%)",
                                    percent=pct,
                                )
                                last_pct = int(pct)
            return True
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, OSError) as e:
            last_err = e
            if win:
                win.update(f"{label_prefix} 재시도 {attempt}/{NETWORK_RETRIES}... ({e})")
            time.sleep(min(2 * attempt, 10))
    raise RuntimeError(f"다운로드 실패({NETWORK_RETRIES}회 재시도): {last_err}")


# ── Ollama 실행 파일 찾기 (PATH 비의존, #7 해결방안 2) ──
def find_ollama_executable():
    found = shutil.which("ollama")
    if found:
        return found
    candidates = []
    for var in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        base = os.environ.get(var)
        if base:
            candidates.append(os.path.join(base, "Programs", "Ollama", "ollama.exe"))
            candidates.append(os.path.join(base, "Ollama", "ollama.exe"))
    candidates.append(os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe"))
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# ── UAC 권한 상승으로 인스톨러 실행 (#7 해결방안 1) ──
def run_installer_elevated(installer_path):
    """ShellExecuteW(runas)로 UAC 동의를 받고 /VERYSILENT로 무인 설치. 종료까지 대기."""
    if not IS_WINDOWS:
        raise OSError("이 기능은 Windows 전용입니다.")

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SEE_MASK_NOASYNC = 0x00000100

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    sei.lpVerb = "runas"
    sei.lpFile = installer_path
    # Inno Setup 옵션: 완전 무인 + 메시지박스 억제 + 재부팅 안 함
    sei.lpParameters = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
    sei.nShow = 1

    ShellExecuteExW = ctypes.windll.shell32.ShellExecuteExW
    ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    ShellExecuteExW.restype = wintypes.BOOL

    if not ShellExecuteExW(ctypes.byref(sei)):
        raise OSError(f"ShellExecuteExW 실패 (errno={ctypes.get_last_error()})")

    if sei.hProcess:
        ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 0xFFFFFFFF)
        ctypes.windll.kernel32.CloseHandle(sei.hProcess)


def _open_url(url):
    try:
        if IS_WINDOWS:
            os.startfile(url)
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception:
        pass


# ── Ollama 확인 및 설치 ───────────────────────────
def ensure_ollama(win):
    win.update("Ollama 확인 중...")
    if find_ollama_executable():
        win.update("[OK] Ollama 이미 설치됨")
        return True

    installer_path = os.path.join(os.environ.get("TEMP", "."), "ollama-setup.exe")
    try:
        win.update("Ollama 다운로드 중... (약 수십 MB)")
        try:
            download_with_resume(
                OLLAMA_INSTALLER_URL, installer_path,
                win=win, label_prefix="Ollama 다운로드",
            )
        except Exception as e:
            # #7 해결방안 3: 명확한 안내 + 다운로드 페이지 열기
            messagebox.showerror(
                "Ollama 다운로드 실패",
                f"자동 다운로드에 {NETWORK_RETRIES}회 재시도 후 실패했습니다.\n\n"
                f"오류: {e}\n\n"
                f"브라우저로 직접 받아 설치한 뒤 SsakSsak.exe를 다시 실행해 주세요.\n"
                f"{OLLAMA_DOWNLOAD_PAGE}"
            )
            _open_url(OLLAMA_DOWNLOAD_PAGE)
            return False

        win.update("Ollama 설치 중... (UAC 권한 동의가 필요합니다)")
        try:
            run_installer_elevated(installer_path)
        except Exception as e:
            messagebox.showerror(
                "Ollama 설치 실패",
                f"인스톨러 실행에 실패했습니다.\n\n"
                f"오류: {e}\n\n"
                f"수동으로 설치해주세요:\n"
                f"  1) 다음 파일을 직접 실행: {installer_path}\n"
                f"  2) 또는 다운로드 페이지에서 받기: {OLLAMA_DOWNLOAD_PAGE}\n\n"
                f"설치 후 SsakSsak.exe를 다시 실행해주세요."
            )
            _open_url(OLLAMA_DOWNLOAD_PAGE)
            return False

        time.sleep(3)
        if find_ollama_executable():
            win.update("[OK] Ollama 설치 완료")
            return True

        messagebox.showerror(
            "Ollama 인식 실패",
            "Ollama를 설치했지만 실행 파일을 찾지 못했습니다.\n"
            "PC를 한 번 재부팅한 뒤 SsakSsak.exe를 다시 실행해주세요."
        )
        return False
    finally:
        # #2 해결방안 2: try/finally로 인스톨러 잔여물 항상 삭제
        if os.path.exists(installer_path):
            try:
                os.remove(installer_path)
            except OSError:
                pass


# ── 모델 확인 및 다운로드 (진행률 + 재시도, #8 해결방안 3) ──
_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0


def ensure_models(win):
    preload = ["llama3.2:3b"]
    ollama_exe = find_ollama_executable() or "ollama"
    try:
        result = subprocess.run(
            [ollama_exe, "list"],
            capture_output=True, text=True, timeout=30,
            creationflags=_NO_WINDOW,
        )
        installed = result.stdout
    except Exception:
        messagebox.showerror("오류", "Ollama 실행 실패. Ollama가 정상 설치됐는지 확인해주세요.")
        return False

    pct_re = re.compile(r"(\d+(?:\.\d+)?)\s*%")

    for model in preload:
        if model in installed:
            win.update(f"[OK] {model} 이미 설치됨")
            time.sleep(0.3)
            continue

        win.update(f"{model} 다운로드 중... (최초 1회, 약 2GB)")
        success = False
        for attempt in range(1, NETWORK_RETRIES + 1):
            proc = None
            try:
                proc = subprocess.Popen(
                    [ollama_exe, "pull", model],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="ignore",
                    bufsize=1,
                    creationflags=_NO_WINDOW,
                )
                last_pct = -1
                start_time = time.time()
                for line in proc.stdout:
                    if time.time() - start_time > MODEL_PULL_HARD_TIMEOUT:
                        proc.kill()
                        raise TimeoutError("모델 다운로드 1시간 초과")
                    line = line.strip()
                    if not line:
                        continue
                    m = pct_re.search(line)
                    if m:
                        pct = float(m.group(1))
                        if int(pct) != last_pct:
                            win.update(f"{model} 다운로드 {pct:.0f}%", percent=pct)
                            last_pct = int(pct)
                    else:
                        win.update(f"{model}: {line[:60]}")
                proc.wait(timeout=60)
                if proc.returncode == 0:
                    success = True
                    break
                win.update(f"{model} 재시도 {attempt}/{NETWORK_RETRIES} (exit={proc.returncode})")
            except (subprocess.TimeoutExpired, TimeoutError) as e:
                if proc and proc.poll() is None:
                    proc.kill()
                win.update(f"{model} 타임아웃, 재시도 {attempt}/{NETWORK_RETRIES}: {e}")
            except Exception as e:
                if proc and proc.poll() is None:
                    proc.kill()
                win.update(f"{model} 오류, 재시도 {attempt}/{NETWORK_RETRIES}: {e}")
            time.sleep(min(2 * attempt, 10))

        if not success:
            messagebox.showerror(
                "모델 다운로드 실패",
                f"{model} 다운로드에 {NETWORK_RETRIES}회 재시도했지만 실패했습니다.\n"
                "네트워크 상태를 확인하고 SsakSsak.exe를 다시 실행해주세요."
            )
            return False
    return True


AUTH_COOKIE_NAME = "ssaksak_auth"
AUTH_QUERY_NAME = "token"


def _install_token_gate(expected_token):
    """Tornado RequestHandler.prepare를 패치해 토큰 게이트 적용.
    - 첫 진입: ?token=xxx → 일치하면 쿠키 발급
    - 이후: 쿠키만으로 통과
    - 둘 다 없으면 403
    """
    if not expected_token:
        return
    try:
        import tornado.web
    except ImportError:
        return

    _original_prepare = tornado.web.RequestHandler.prepare

    def _auth_prepare(self):
        try:
            query_token = self.get_query_argument(AUTH_QUERY_NAME, default=None)
        except Exception:
            query_token = None
        if query_token == expected_token:
            self.set_cookie(
                AUTH_COOKIE_NAME, expected_token,
                httponly=True, samesite="Strict",
            )
            return _original_prepare(self)
        if self.get_cookie(AUTH_COOKIE_NAME) == expected_token:
            return _original_prepare(self)
        # 헬스체크/스타트업 핑은 허용 (서버 살아있는지 외부에서 확인 가능)
        if self.request.path in ("/_stcore/health", "/healthz"):
            return _original_prepare(self)
        self.set_status(403)
        self.finish("Forbidden")
        return None

    tornado.web.RequestHandler.prepare = _auth_prepare


# ── Streamlit 자식 프로세스 진입점 (multiprocessing, #6 해결방안 3) ──
def run_streamlit(port):
    # --windowed 빌드에서 자식 프로세스의 stdout/stderr 가 None 이어서
    # 예외 발생 시 AttributeError: 'NoneType' object has no attribute 'write' 가 뜸
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')

    app_path = resource_path('app.py')

    if getattr(sys, 'frozen', False):
        static_path = resource_path(os.path.join('streamlit', 'static'))
        os.environ['STREAMLIT_STATIC_PATH'] = static_path

    # 토큰 게이트 설치 — streamlit이 Tornado 핸들러를 만들기 전에 RequestHandler를 패치
    _install_token_gate(os.environ.get("SSAKSSAK_TOKEN", ""))

    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        f"--server.port={port}",
        # #5 해결방안 1: 루프백만 바인딩 + XSRF 보호 ON (enableXsrfProtection 옵션 제거 = 기본값 true)
        "--server.address=127.0.0.1",
        "--server.enableCORS=false",
        "--server.fileWatcherType=none",
    ]
    from streamlit.web import cli as stcli
    stcli.main()


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_for_server(port, timeout=30):
    token = os.environ.get("SSAKSSAK_TOKEN", "")
    url = f"http://127.0.0.1:{port}/?{AUTH_QUERY_NAME}={token}" if token else f"http://127.0.0.1:{port}"
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError as e:
            # 4xx 라도 응답이 왔다면 서버는 살아있음
            if e.code in (200, 401, 403):
                return True
        except Exception:
            time.sleep(0.5)
    return False


# ── Ollama 수명 주기 관리 ────────────────────────────
# 앱이 실행 중일 때만 Ollama를 띄우고, 창 닫으면 같이 종료한다.
# 이미 다른 방법으로 Ollama가 실행 중이면 간섭하지 않는다.
_streamlit_proc = None
_ollama_proc = None       # 우리가 직접 시작한 ollama serve 프로세스
_we_started_ollama = False


def is_ollama_api_ready():
    """포트 11434에 Ollama API가 응답하는지 확인."""
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2)
        return True
    except Exception:
        return False


def start_ollama_if_needed(win=None):
    """Ollama가 실행 중이 아니면 'ollama serve'를 직접 띄운다.
    이미 실행 중이면 아무것도 하지 않는다."""
    global _ollama_proc, _we_started_ollama

    if is_ollama_api_ready():
        _we_started_ollama = False
        return True

    ollama_exe = find_ollama_executable()
    if not ollama_exe:
        return False

    if win:
        win.update("Ollama 서버 시작 중...")

    _ollama_proc = subprocess.Popen(
        [ollama_exe, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )
    _we_started_ollama = True

    for _ in range(30):
        if is_ollama_api_ready():
            return True
        time.sleep(0.5)

    return False


def cleanup():
    """Streamlit + (우리가 시작한 경우) Ollama 프로세스 종료.
    atexit / webview closed 양쪽에서 호출된다."""
    global _streamlit_proc, _ollama_proc, _we_started_ollama

    # Streamlit 자식 종료
    proc = _streamlit_proc
    _streamlit_proc = None
    if proc is not None:
        try:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=5)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=2)
        except Exception:
            pass

    # 우리가 시작한 Ollama만 종료 (기존 서비스엔 손대지 않음)
    if _we_started_ollama:
        oproc = _ollama_proc
        _ollama_proc = None
        _we_started_ollama = False
        if oproc is not None and oproc.poll() is None:
            try:
                oproc.terminate()
                oproc.wait(timeout=5)
            except Exception:
                try:
                    oproc.kill()
                except Exception:
                    pass


# ── 메인 ─────────────────────────────────────────
def main():
    global _streamlit_proc

    # #6 해결방안 2: 어떤 경로로 종료되든 cleanup 보장
    atexit.register(cleanup)

    # 0. #2 해결방안 3: 시작 시 %TEMP%의 ollama-setup* 잔재 청소
    cleanup_old_artifacts()

    # #5 해결방안 (a): 시작마다 새 랜덤 토큰을 환경변수로 자식 프로세스에 전달
    # 같은 PC의 다른 프로세스가 localhost:port를 두드려도 토큰 없이는 403
    os.environ["SSAKSSAK_TOKEN"] = secrets.token_urlsafe(32)

    # 1. 설치 팝업
    win = SetupWindow()

    if not ensure_ollama(win):
        win.close()
        sys.exit(1)

    # Ollama 서버가 떠 있지 않으면 직접 시작 — 창 닫힐 때 같이 종료됨
    if not start_ollama_if_needed(win):
        win.close()
        messagebox.showerror("오류", "Ollama 서버를 시작할 수 없습니다. 재설치 후 다시 실행해주세요.")
        sys.exit(1)

    if not ensure_models(win):
        win.close()
        sys.exit(1)

    win.update("앱 서버 시작 중...")

    # 2. 빈 포트 찾기
    port = find_free_port()

    # 3. Streamlit을 자식 프로세스로 띄움 — 부모 종료 시 PID 단위 정리 가능
    _streamlit_proc = mp.Process(target=run_streamlit, args=(port,), daemon=True)
    _streamlit_proc.start()

    # 4. 서버 응답 대기
    if not wait_for_server(port, timeout=30):
        win.close()
        cleanup()
        messagebox.showerror("오류", "서버 시작 실패. 다시 실행해주세요.")
        sys.exit(1)

    win.close()

    # 5. pywebview로 데스크탑 창 열기 (메인 스레드)
    # 첫 GET에 토큰 쿼리를 실어서 보냄 → 서버가 쿠키 발급 → 이후 요청은 쿠키만으로 통과
    import webview
    token = os.environ.get("SSAKSSAK_TOKEN", "")
    initial_url = f"http://127.0.0.1:{port}/?{AUTH_QUERY_NAME}={token}" if token else f"http://127.0.0.1:{port}"
    window = webview.create_window(
        "싹싹번역 - 강의자료 번역기",
        initial_url,
        width=1280,
        height=860,
        resizable=True,
    )
    # #6 해결방안 1: 창이 닫히면 즉시 streamlit 자식 프로세스 종료
    window.events.closed += cleanup
    webview.start()
    cleanup()


if __name__ == "__main__":
    # PyInstaller --onedir + --windowed 환경에서 multiprocessing 동작 보장
    mp.freeze_support()
    main()
