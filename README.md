# EduTrans 🎓

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

### 사전 요구사항
- Python 3.10 이상

### 설치 및 실행

1. [Releases](https://github.com/seoyeon59/EduTrans/releases)에서 최신 버전 zip 다운로드
2. 압축 해제 후 `run.bat` **우클릭 → 관리자 권한으로 실행**
3. 자동으로 아래 과정이 진행됩니다:
   - Ollama 설치 (미설치 시)
   - AI 모델 다운로드 (`qwen2.5:3b`, `llama3.2:3b` — 최초 1회, 약 4GB)
   - Python 패키지 설치
   - 브라우저에서 앱 자동 실행

> 최초 실행 시 모델 다운로드로 인해 시간이 소요될 수 있습니다.

---

## AI 모델

| 모델 | 분류 |  특징 |
|------|------|------|
| **qwen2.5:3b** | RAM 8GB+ | 최고 번역 품질 |
| **llama3.2:3b** | RAM 8GB+ | 빠름 |

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 엔진 | [Ollama](https://ollama.com) |
| PDF 처리 | PyMuPDF (fitz) |
| PPT 처리 | python-pptx |
| UI | Streamlit |
| 언어 | Python 3.10+ |

---

## 프로젝트 구조

```
EduTrans/
├── app.py            # 메인 Streamlit 앱
├── glossary.py       # 전공별 용어 사전
├── build_run.py      # 데스크탑 생상
├── requirements.txt  # Python 패키지 목록
└── build_exe.bat           # 설치 및 실행 스크립트 (Windows)
```

---

## 라이선스

이 프로젝트는 다음 AI 모델을 사용합니다:

- **Qwen2.5** — [Qwen Research License](https://huggingface.co/Qwen/Qwen2.5-3B/blob/main/LICENSE)  
  비상업적·연구·교육 목적에 한함 © Alibaba Cloud
- **Llama 3.2** — [Meta Llama Community License](https://llama.meta.com/llama3/license/)  
  월간 활성 사용자 7억 명 미만 서비스에 한해 상업적 사용 허용 © Meta Platforms, Inc.
