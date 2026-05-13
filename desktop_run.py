import sys
import os
import threading
import time
import webbrowser


def resource_path(relative_path):
    """PyInstaller .exe 내부 경로와 일반 실행 경로 모두 처리"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def run_streamlit():
    app_path = resource_path('app.py')

    # PyInstaller frozen 모드에서 Streamlit 정적 파일 경로 수동 지정
    if getattr(sys, 'frozen', False):
        static_path = resource_path(os.path.join('streamlit', 'static'))
        os.environ['STREAMLIT_STATIC_PATH'] = static_path

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--server.port=8501",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.fileWatcherType=none",  # frozen 환경에서 파일 감시 비활성화
    ]

    # windowed 모드에서 stdout/stderr 리다이렉트 (없으면 crash)
    if getattr(sys, 'frozen', False):
        log_path = os.path.join(os.path.dirname(sys.executable), 'edutrans.log')
        sys.stdout = open(log_path, 'w', encoding='utf-8')
        sys.stderr = sys.stdout

    from streamlit.web import cli as stcli
    stcli.main()


def wait_for_server(url, timeout=30):
    import urllib.request
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    if wait_for_server("http://localhost:8501", timeout=30):
        webbrowser.open("http://localhost:8501")
    else:
        # 서버 시작 실패 시 로그 위치 안내
        if getattr(sys, 'frozen', False):
            log_path = os.path.join(os.path.dirname(sys.executable), 'edutrans.log')
            import tkinter.messagebox as mb
            mb.showerror(
                "EduTrans 오류",
                f"서버 시작에 실패했습니다.\n오류 로그: {log_path}"
            )
        sys.exit(1)

    t.join()
