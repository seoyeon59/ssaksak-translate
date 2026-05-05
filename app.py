import streamlit as st
import fitz  # PyMuPDF
import os
import re
import unicodedata
import tempfile
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from langchain_ollama import OllamaLLM

# --- [1. 초기 설정 및 모델 엔진] ---
st.set_page_config(page_title="TransSlide AI - 로컬 전공 번역기", layout="wide", page_icon="🎓")

# 세션 상태 초기화 (캐시 및 자동 감지 결과 저장)
if 'translation_cache' not in st.session_state:
    st.session_state['translation_cache'] = {}
if 'detected_dept' not in st.session_state:
    st.session_state['detected_dept'] = None

# 전공별 용어 사전 (사용자 기존 코드 유지)
GLOSSARY = {
    "Data Science": {"Deep Learning": "딥러닝", "Inference": "추론", "Backpropagation": "역전파"},
    "Business Administration": {"Asset": "자산", "Equity": "자본", "Liability": "부채"},
    "Nursing": {"Diagnosis": "진단", "Intervention": "중재", "Outcome": "결과"}
}

# --- [2. 사이드바 UI: 엔진 및 전공 설정] ---
with st.sidebar:
    st.header("⚙️ 엔진 설정 (운영비 0원)")
    selected_model = st.selectbox(
        "사용할 AI 모델 선택",
        ["phi3", "llama3"],
        index=0,
        help="저사양(8GB RAM)은 phi3를, 고사양(GPU 8GB+)은 llama3를 권장합니다."
    )

    # LLM 인스턴스 생성 (선택된 모델 적용)
    llm = OllamaLLM(model=selected_model, temperature=0)

    st.divider()
    st.header("🏫 전공 및 과목 설정")

    # 자동 감지 옵션 추가
    auto_detect = st.checkbox("🔍 전공 자동 감지 모드", value=True, help="첫 페이지를 분석해 전공을 스스로 판단합니다.")

    category = st.radio("1. 계열 선택", ["문과 (Humanities)", "이과 (Science & Engineering)", "예체능 (Arts & Sports)"])

    dept_map = {
        "문과 (Humanities)": [
            "Business Administration", "Economics", "Marketing", "Accounting",
            "International Relations", "Psychology", "Sociology",
            "Media & Communication", "English Language & Literature", "Political Science"
        ],
        "이과 (Science & Engineering)": [
            "Computer Science", "Data Science", "Artificial Intelligence Engineering",
            "Electrical Engineering", "Mechanical Engineering", "Chemical Engineering",
            "Biotechnology", "Nursing", "Architecture", "Civil Engineering",
            "Mathematics", "Physics", "Medical"
        ],
        "예체능 (Arts & Sports)": [
            "Fine Arts", "Graphic Design", "Industrial Design", "Music Composition",
            "Vocal Music", "Physical Education", "Film & Digital Media", "Fashion Design"
        ]
    }
    manual_dept = st.selectbox("2. 세부 전공 선택", dept_map[category])

    # 현재 적용 중인 전공 표시
    display_dept = st.session_state['detected_dept'] if (
                auto_detect and st.session_state['detected_dept']) else manual_dept
    st.info(f"📍 현재 적용 문맥: **{display_dept}**")

    st.divider()
    if st.button("🧹 번역 캐시 초기화"):
        st.session_state['translation_cache'] = {}
        st.session_state['detected_dept'] = None
        st.success("캐시가 초기화되었습니다.")


# --- [3. 핵심 엔지니어링 유틸리티 (기존 로직 유지)] ---

def normalize_for_cache(text):
    return re.sub(r'\s+', ' ', text.lower().strip())


def clean_text_logic(text):
    text = unicodedata.normalize('NFKC', text)
    text = text.replace("-\n", "").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()


def is_english_content(text):
    return any(c.isalpha() for c in text)


def detect_major_from_text(text):
    """[추가] 첫 페이지 텍스트로 전공 자동 추론"""
    if not text.strip(): return "General"
    prompt = (
        f"Analyze this text from a lecture slide and identify the academic major. "
        f"Answer with ONLY the name of the major in English.\n\nText: {text[:500]}\nMajor:"
    )
    try:
        return str(llm.invoke(prompt)).strip()
    except:
        return "General"


def translate_single(text, department):
    """기존의 용어 사전 및 '순수 해석' 프롬프트 유지"""
    cleaned = clean_text_logic(text)
    if len(cleaned) < 1: return text

    norm_key = normalize_for_cache(cleaned)
    if norm_key in st.session_state['translation_cache']:
        return st.session_state['translation_cache'][norm_key]

    glossary_hint = ""
    if department in GLOSSARY:
        terms = [f"{k}:{v}" for k, v in GLOSSARY[department].items()]
        glossary_hint = f"(용어 강제: {', '.join(terms)})"

    prompt = (
        f"You are a professional translator for {department} students. "
        f"Your ONLY job is to output the Korean translation of the given text. "
        f"STRICT RULE: NEVER explain. Output ONLY the translation.\n\n"
        f"{glossary_hint}\nEnglish: {cleaned}\nKorean:"
    )

    try:
        translated = str(llm.invoke(prompt)).strip()
        if not translated or translated == cleaned: return ""

        # 모델 잡설 제거 로직
        translated = re.sub(r'^(번역:|결과:|Translated:|해석:|Korean:)', '', translated, flags=re.IGNORECASE).strip()
        translated = re.sub(r'^[" \']+|[" \']+$', '', translated).strip()

        st.session_state['translation_cache'][norm_key] = translated
        return translated
    except Exception as e:
        st.error(f"Ollama 연결 확인 필요: {e}")
        return text


# --- [4. 문서 처리 함수 (진행 바 및 레이아웃 유지)] ---

def process_pptx(input_path, output_path, dept, auto_detect_flag):
    prs = Presentation(input_path)
    total_slides = len(prs.slides)
    progress_bar = st.progress(0)
    status_text = st.empty()

    # [추가] 자동 전공 감지 실행
    if auto_detect_flag and total_slides > 0:
        first_text = ""
        for shape in prs.slides[0].shapes:
            if hasattr(shape, "text"): first_text += shape.text + " "
        st.session_state['detected_dept'] = detect_major_from_text(first_text)
        dept = st.session_state['detected_dept']

    for i, slide in enumerate(prs.slides):
        status_text.text(f"슬라이드 {i + 1}/{total_slides} 번역 중... (전공: {dept})")
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    original_text = "".join(run.text for run in paragraph.runs).strip()
                    if len(original_text) < 2 or not is_english_content(original_text):
                        continue

                    translated = translate_single(original_text, dept)
                    if translated and translated != original_text:
                        run = paragraph.add_run()
                        run.text = f"\n{translated}"
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0, 102, 204)
        progress_bar.progress((i + 1) / total_slides)
    prs.save(output_path)
    status_text.text("✅ PPT 번역 완료!")


def process_pdf(input_path, output_path, dept):
    doc = fitz.open(input_path)
    total_pages = len(doc)
    progress_bar = st.progress(0)
    status_text = st.empty()
    font_path = "C:/Windows/Fonts/malgun.ttf"  # Windows 기준

    for i, page in enumerate(doc):
        status_text.text(f"페이지 {i + 1}/{total_pages} 번역 중...")
        blocks = page.get_text("blocks")
        for b in blocks:
            full_text = b[4].replace("\n", " ").strip()
            if len(full_text) < 2 or not is_english_content(full_text): continue

            translated = translate_single(full_text, dept)
            if translated and translated.strip() != "":
                # 텍스트 바로 아래(b[3]+5)에 삽입
                page.insert_text((b[0], b[3] + 5), translated,
                                 fontname="ko", fontfile=font_path,
                                 fontsize=9, color=(0, 0.2, 0.6))
        progress_bar.progress((i + 1) / total_pages)
    doc.save(output_path)
    doc.close()
    status_text.text("✅ PDF 번역 완료!")


# --- [5. Streamlit UI 메인 구성 (기존 스타일 유지)] ---
st.markdown("""<style>
    .stSidebar h2 { font-size: 1.8rem !important; color: #4A90E2; }
    .stButton button { width: 100%; background-color: #4A90E2 !important; color: white !important; border-radius: 10px; }
</style>""", unsafe_allow_html=True)

st.title("🎓 전공 맞춤형 강의자료 번역기")

with st.expander("📖 이용 가이드 및 주의사항", expanded=False):
    st.markdown("""
    1. **로컬 엔진:** Ollama가 실행 중이어야 합니다 (`ollama serve`).
    2. **모델 선택:** 저사양은 **phi3**, 고사양은 **llama3**를 권장합니다.
    3. **자동 감지:** 첫 슬라이드를 분석해 전공 문맥을 자동으로 설정합니다.
    4. **보안:** 모든 데이터는 본인 PC 내에서만 처리되어 안전합니다.
    """)

tab1, tab2 = st.tabs(["📊 PPT 번역", "📄 PDF 번역"])


def run_translation(uploaded_file, mode):
    if uploaded_file:
        if st.button(f"🚀 {mode} 번역 시작"):
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
                tmp_in.write(uploaded_file.getvalue())
                in_path = tmp_in.name

            out_path = os.path.join(tempfile.gettempdir(), f"translated_{uploaded_file.name}")
            try:
                with st.spinner(f"{selected_model} 모델이 문맥 분석 및 번역 중..."):
                    if mode == "PPTX":
                        process_pptx(in_path, out_path, manual_dept, auto_detect)
                    else:
                        process_pdf(in_path, out_path, manual_dept)
                st.success("✅ 처리가 완료되었습니다!")
                with open(out_path, "rb") as f:
                    st.download_button("💾 결과 다운로드", f, file_name=f"translated_{uploaded_file.name}")
            except Exception as e:
                st.error(f"오류 발생: {e}")
            finally:
                if os.path.exists(in_path): os.remove(in_path)


with tab1: run_translation(st.file_uploader("PPTX 업로드", type="pptx", key="p1"), "PPTX")
with tab2: run_translation(st.file_uploader("PDF 업로드", type="pdf", key="p2"), "PDF")

st.divider()
st.markdown("<p style='text-align: center; color: gray;'>Powered by Ollama & Streamlit</p>", unsafe_allow_html=True)