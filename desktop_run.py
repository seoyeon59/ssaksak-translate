import webview
import subprocess
import time
import os
import sys


# 1. Streamlit 서버를 백그라운드에서 실행
def run_streamlit():
    # 현재 파일의 경로를 기준으로 main.py(팀장님 코드) 위치 지정
    cmd = ["streamlit", "run", "main.py", "--server.headless", "true", "--server.port", "8501"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == "__main__":
    # 서버 시작
    p = run_streamlit()

    # 서버가 뜰 때까지 잠시 대기
    time.sleep(5)

    # 2. 전용 윈도우 창 띄우기 (카카오톡/크롬처럼 보이게 함)
    webview.create_window("EduTrans Pro - 강의자료 번역기", "http://localhost:8501",
                          width=1200, height=800, resizable=True)
    webview.start()

    # 창을 닫으면 서버 프로세스도 함께 종료
    p.kill()