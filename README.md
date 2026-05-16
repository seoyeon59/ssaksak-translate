# 싹싹번역 🎓

**전공 문맥 파악 및 레이아웃 유지형 로컬 번역 솔루션**

강의 슬라이드의 전문 용어를 전공 맥락에 맞게 번역하면서, 원본 레이아웃을 그대로 유지합니다.
모든 처리는 내 PC에서 완결 — 외부 서버 전송 없음, API 비용 없음.

`#Zero_Cost` `#On_Device_AI` `#Privacy_First` `#Major_Optimized`

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **전공 자동 감지** | 첫 슬라이드 키워드를 AI가 분석해 학문 분야를 스스로 판단 |
| **레이아웃 유지 번역** | 원본 텍스트 바로 아래에 파란색으로 번역문 삽입, 좌표·폰트 크기 보존 |
| **코드 블록 인식** | 코드는 번역하지 않고 한 줄 한국어 주석(`# 설명`) 자동 생성 |
| **전공별 용어 사전** | 전공별 100 단어의 전문 용어 내장, 사용자 커스텀 용어 추가 가능 |
| **On-Device AI** | Ollama 기반 로컬 추론, 인터넷 없이 무제한 사용 (모델 다운로드 후) |

**지원 파일 형식:** PDF, PPTX

---

## 빠른 시작

### 시스템 요구사항
- Windows 10/11 (64-bit)
- RAM 8GB 이상 (모델 추론용)
- 디스크 여유 공간 약 3GB (모델 + 앱)

### 설치 및 실행

1. [Releases](https://github.com/seoyeon59/SsakSsak/releases)에서 최신 `SsakSsak-x.x.x-win64.zip` 다운로드
2. 압축 해제 후 `SsakSsak.exe` 더블클릭
3. 자동으로 아래 과정이 진행됩니다:
   - Ollama 자동 설치 (미설치 시 UAC 동의 1회)
   - AI 모델 다운로드 (`llama3.2:3b` — 최초 1회, 약 2GB)
   - 데스크톱 창에서 앱 자동 실행

> 최초 실행 시 모델 다운로드(약 2GB)로 시간이 소요될 수 있습니다. 두 번째 실행부터는 즉시 시작합니다.

---

### ⚠️ 첫 실행 시 SmartScreen 경고가 뜬다면

싹싹번역은 아직 코드 사이닝 인증서를 적용하지 않은 상태입니다. 그래서 **첫 실행 시 Windows에서 다음과 같은 보호 화면**이 뜰 수 있습니다:

```
Windows에서 PC를 보호했습니다
인식할 수 없는 앱의 시작을 Microsoft Defender SmartScreen에서 차단했습니다.
```

**해결 방법:**

1. 경고 창에서 **"추가 정보(More info)"** 클릭
2. 하단에 나타난 **"실행(Run anyway)"** 버튼 클릭

이는 코드 사이닝 인증서가 없는 모든 오픈소스 앱에서 발생하는 정상 동작이며, 다운로드 수가 누적되면 SmartScreen 평판이 자연스럽게 좋아져 경고가 사라집니다. 보안이 걱정되시면 [소스 코드](https://github.com/seoyeon59/SsakSsak)를 직접 확인하고 빌드하실 수도 있습니다.

> 모든 데이터는 사용자 PC에서만 처리되며, 외부 서버로 어떤 파일도 전송되지 않습니다.

---

## AI 모델

| 모델 | 크기 | 라이선스 | 특징 |
|------|------|---------|------|
| **llama3.2:3b** | ~2GB | Llama 3.2 Community License | Meta의 경량 3B 모델. 빠른 속도와 충분한 한국어 번역 품질 |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 엔진 | [Ollama](https://ollama.com) + [Llama 3.2 3B](https://llama.meta.com/) |
| PDF 처리 | PyMuPDF (fitz) |
| PPT 처리 | python-pptx |
| 데스크톱 셸 | pywebview + Streamlit |
| 패키징 | PyInstaller + Inno Setup |
| 언어 | Python 3.10+ |

---

## 프로젝트 구조

```
SsakSsak/
├── app.py            # 메인 Streamlit 앱 (UI + 번역 로직)
├── glossary.py       # 전공별 기본 용어 사전
├── desktop_run.py    # 데스크톱 진입점 (Ollama 설치, webview 실행)
├── fonts/            # 한글 폰트 (PDF 번역에 사용)
│   └── NanumGothic.ttf
├── requirements.txt  # Python 패키지 목록
├── build_exe.bat     # PyInstaller 빌드 스크립트
├── installer.iss     # Inno Setup 설치 마법사 스크립트
└── icon.ico          # 앱 아이콘
```

> **이름 규칙**: 사용자에게 보이는 이름은 한글 **싹싹번역**, 파일/폴더/실행 파일명은 ASCII **SsakSsak** 으로 통일합니다 (CI·압축·이메일 첨부 호환성).

---

## 직접 빌드하기 (개발자용)

소스에서 EXE를 직접 만들고 싶다면:

```bash
# 1. 의존성 설치
pip install -r requirements.txt
pip install pyinstaller pywebview

# 2. fonts/ 폴더에 NanumGothic.ttf 등 한글 TTF 넣기
#    (네이버 나눔글꼴 https://hangeul.naver.com/font 에서 다운로드)

# 3. EXE 빌드 → dist/SsakSsak/SsakSsak.exe 생성
build_exe.bat

# 4. (선택) Inno Setup으로 설치 마법사 만들기
#    https://jrsoftware.org/isinfo.php 에서 Inno Setup 설치 후
#    installer.iss 우클릭 → Compile
```

**배포 패키징 옵션:**
- **간단한 배포**: `dist/SsakSsak/` 폴더를 통째로 ZIP으로 압축해 GitHub Release에 업로드
- **설치 마법사 배포**: Inno Setup으로 `installer.iss`를 컴파일 → 단일 `SsakSsak-Setup.exe` 생성

### 자동 배포 (GitHub Actions)

`.github/workflows/release.yml` 이 설정되어 있어, 태그 한 번이면 자동 빌드·릴리즈됩니다:

```bash
# 1. 새 버전 태그 만들고 푸시
git tag v1.0.0
git push origin v1.0.0

# 2. GitHub Actions가 자동으로:
#    - Windows runner에서 PyInstaller 빌드
#    - NanumGothic 폰트 자동 다운로드
#    - ZIP 압축 + Inno Setup 설치 마법사 컴파일
#    - GitHub Release 생성 후 두 파일 모두 업로드

# 수동 실행도 가능: GitHub 저장소 → Actions 탭 → "Build & Release" → Run workflow
```

---

## 라이선스

이 프로젝트는 다음 AI 모델을 사용합니다:

- **Llama 3.2** — [Meta Llama Community License](https://llama.meta.com/llama3/license/)
  월간 활성 사용자 7억 명 미만 서비스에 한해 상업적 사용 허용 © Meta Platforms, Inc.


## 문의사항
싹싹 번역 이용 불편 : [https://forms.gle/QEyvksf7CHGqRzDs9]
메일 : swu.iwantrest@gmail.com
