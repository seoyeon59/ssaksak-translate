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
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--server.port=8501",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
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
    # Streamlit을 백그라운드 스레드에서 실행
    t = threading.Thread(target=run_streamlit, daemon=True)
    t.start()

    # 서버가 실제로 응답할 때까지 대기
    if wait_for_server("http://localhost:8501", timeout=30):
        webbrowser.open("http://localhost:8501")
    else:
        print("서버 시작 실패. Ollama가 실행 중인지 확인하세요.")
        sys.exit(1)

    # 메인 스레드 유지 (창 닫힐 때까지)
    t.join()
