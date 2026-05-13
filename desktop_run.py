import sys
import os
import threading
import time
import webview


def get_app_path():
    """exe로 실행할 때와 일반 실행 때 모두 app.py 경로를 올바르게 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 패키징된 .exe 실행 시
        return os.path.join(os.path.dirname(sys.executable), 'app.py')
    else:
        # 일반 python 실행 시
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')


def run_streamlit(app_path):
    """Streamlit을 subprocess 없이 내부에서 직접 실행"""
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
    """서버가 응답할 때까지 대기 (최대 timeout초)"""
    import urllib.request
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    app_path = get_app_path()

    if not os.path.exists(app_path):
        import tkinter.messagebox as mb
        mb.showerror("EduTrans 오류", f"app.py를 찾을 수 없습니다.\n경로: {app_path}")
        sys.exit(1)

    # Streamlit을 백그라운드 스레드에서 실행
    t = threading.Thread(target=run_streamlit, args=(app_path,), daemon=True)
    t.start()

    # 서버가 실제로 응답할 때까지 대기
    print("서버 시작 중...")
    ready = wait_for_server("http://localhost:8501", timeout=30)

    if not ready:
        import tkinter.messagebox as mb
        mb.showerror("EduTrans 오류", "서버 시작 실패. Ollama가 실행 중인지 확인해주세요.")
        sys.exit(1)

    # 웹뷰 창 열기
    webview.create_window(
        "EduTrans - 강의자료 번역기",
        "http://localhost:8501",
        width=1200,
        height=800,
        resizable=True,
    )
    webview.start()
