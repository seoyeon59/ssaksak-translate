import streamlit as st
import fitz  # PyMuPDF
import os
import re
import unicodedata
import tempfile
import pytesseract
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from langchain_ollama import OllamaLLM

# --- [1. 모델 및 캐시 설정] ---
# 로컬 모델의 특성을 고려해 가장 간결하고 명확한 설정 유지
llm = OllamaLLM(model="llama3", temperature=0)

if 'translation_cache' not in st.session_state:
    st.session_state['translation_cache'] = {}

# 전공별 용어 사전 (Glossary)
GLOSSARY = {
    "Data Science": {"Deep Learning": "딥러닝", "Inference": "추론", "Backpropagation": "역전파"},
    "Business Administration": {"Asset": "자산", "Equity": "자본", "Liability": "부채"},
    "Nursing": {"Diagnosis": "진단", "Intervention": "중재", "Outcome": "결과"}
}


# --- [2. 핵심 엔지니어링 유틸리티] ---

def normalize_for_cache(text):
    """[수정] 캐시 적중률 향상을 위한 정규화 (개선점 3)"""
    return re.sub(r'\s+', ' ', text.lower().strip())


def clean_text_logic(text):
    """[수정] PDF/PPT 특유의 불필요한 기호 및 줄바꿈 제거 (개선점 5)"""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace("-\n", "").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()


def is_english_content(text):
    """[수정] 알파벳 비율 기반 번역 대상 판별 (개선점 6)"""
    alphas = [c for c in text if c.isalpha()]
    if not alphas: return False
    eng_count = len([c for c in alphas if re.match(r'[a-zA-Z]', c)])
    return (eng_count / len(alphas)) > 0.3


def translate_single(text, department):
    """[수정] 불필요한 설명 없이 '순수 해석'만 출력하도록 프롬프트 최적화"""
    cleaned = clean_text_logic(text)
    if len(cleaned) < 2: return text

    norm_key = normalize_for_cache(cleaned)
    if norm_key in st.session_state['translation_cache']:
        return st.session_state['translation_cache'][norm_key]

    glossary_hint = ""
    if department in GLOSSARY:
        terms = [f"{k}:{v}" for k, v in GLOSSARY[department].items()]
        glossary_hint = f"(용어 강제: {', '.join(terms)})"

    # [수정] 모델이 인사말이나 설명을 절대 하지 못하도록 명령 체계 단순화
    prompt = (
        f"Task: Professional translation from English to Korean\n"
        f"Field: {department}\n"
        f"Terminology: {glossary_hint}\n"
        f"Constraint: Output ONLY the Korean translation. No English, no explanations.\n"
        f"Text to translate: {cleaned}"
    )

    try:
        translated = str(llm.invoke(prompt)).strip()
        # [수정] 혹시라도 포함될 수 있는 불필요한 문구(예: 'Translated:', 'Here is...') 제거 로직
        translated = re.sub(r'^(번역:|결과:|Translated:|"|\')', '', translated).strip()
        translated = re.sub(r'("|\|)$', '', translated).strip()

        st.session_state['translation_cache'][norm_key] = translated
        return translated
    except:
        return text

# --- [3. 문서 처리 함수 (진행 바 완벽 적용)] ---

def process_pptx(input_path, output_path, dept):
    prs = Presentation(input_path)
    total_slides = len(prs.slides)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, slide in enumerate(prs.slides):
        status_text.text(f"슬라이드 {i + 1}/{total_slides} 번역 중...")
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    # 문단 전체 텍스트 병합 후 번역
                    original_text = "".join(run.text for run in paragraph.runs).strip()
                    if len(original_text) < 2: continue

                    translated = translate_single(original_text, dept)
                    if translated and translated != original_text:
                        # [수정] 원문 뒤에 번역문 추가
                        run = paragraph.add_run()
                        run.text = f"\n({translated})"
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0, 102, 204)
        progress_bar.progress((i + 1) / total_slides)
    prs.save(output_path)
    status_text.text("PPT 번역 완료!")


def process_pdf(input_path, output_path, dept):
    """[수정] 일반 강의자료 PDF 번역: 원문 하단에 한국어 삽입"""
    doc = fitz.open(input_path)
    total_pages = len(doc)
    progress_bar = st.progress(0)
    font_path = "C:/Windows/Fonts/malgun.ttf"

    for i, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] != 0: continue
            full_text = " ".join(["".join([s["text"] for s in l["spans"]]) for l in b["lines"]]).strip()
            translated = translate_single(full_text, dept)
            if translated and translated != full_text:
                rect = fitz.Rect(b["bbox"])
                f_size = b["lines"][0]["spans"][0]["size"]
                page.insert_text((rect[0], rect[3] + 2), translated,
                                 fontname="ko", fontfile=font_path, fontsize=f_size * 0.7, color=(0, 0.2, 0.6))
        progress_bar.progress((i + 1) / total_pages)
    doc.save(output_path)
    doc.close()


def process_paper(input_path, output_path, dept):
    """[수정] 논문 번역 함수 분리 및 복구: 원문 가리고 한국어로 덮어쓰기"""
    doc = fitz.open(input_path)
    total_pages = len(doc)
    progress_bar = st.progress(0)
    font_path = "C:/Windows/Fonts/malgun.ttf"

    for i, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] != 0: continue
            full_text = " ".join(["".join([s["text"] for s in l["spans"]]) for l in b["lines"]]).strip()
            translated = translate_single(full_text, dept)
            if translated and translated != full_text:
                rect = fitz.Rect(b["bbox"])
                # [수정] 원문을 흰색 상자로 가린 후 그 위에 번역문 작성
                page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
                page.insert_textbox(rect, translated, fontname="ko", fontfile=font_path,
                                    fontsize=9, align=0)
        progress_bar.progress((i + 1) / total_pages)
    doc.save(output_path)
    doc.close()


# --- [4. Streamlit UI 구성] ---
st.set_page_config(page_title="EduTrans - 전공자료 번역기", layout="centered", page_icon="🎓")

st.markdown("""<style>
    .stSidebar h2 { font-size: 2.2rem !important; color: #4A90E2; }
    div[data-testid="stSelectbox"] label { font-size: 1.1rem !important; font-weight: bold !important; }
    .stButton button { width: 100%; height: 3rem; font-size: 1.2rem !important; background-color: #4A90E2 !important; color: white !important; border-radius: 10px; }
</style>""", unsafe_allow_html=True)

st.title("🎓 전공 맞춤형 강의자료 번역기")

# 상세 이용 가이드 가이드라인
with st.expander("📖 EduTrans 이용 가이드 (클릭하여 확인)", expanded=False):
    st.markdown("""
    ### **이용 순서**
    1. **왼쪽 사이드바**에서 본인의 **계열(문/이/예)**을 먼저 선택합니다.
    2. 나타나는 리스트에서 본인의 **세부 전공**을 고릅니다. 전공에 따라 용어 처리가 달라집니다.
    3. 상단 탭에서 파일 형식(**PPT, PDF, 논문**)을 선택한 뒤 파일을 업로드합니다.
    4. **번역 시작** 버튼을 누르고 잠시 기다린 후, 결과 파일을 다운로드합니다.
    5. **번역 캐시** 버튼을 눌러주세요. 동일한 문장은 다시 번역하지 않아 속도가 매우 빠릅니다. 전공을 바꿨다면 '캐시 초기화'를 눌러주세요.
    
    ### **⚠️ 주의사항 (필독)**
    * **페이지 제한**: **50페이지 이상**의 자료는 업로드하지 마세요. (로컬 LLM 자원 한계로 인한 시스템 다운 방지)
    * **단일 파일 원칙**: 동시에 **여러 개**의 파일을 업로드할 수 없습니다. 하나씩 번역해 주세요.
    * **서버 상태**: 로컬 LLM(Ollama)이 실행 중이어야 합니다.
    * **글꼴**: Windows 환경의 '맑은 고딕' 경로를 기본으로 사용합니다.
    * **보안**: 로컬에서 처리되므로 외부로 데이터가 유출되지 않습니다.
    * **한계**: 수식이나 복잡한 표 내부 이미지는 번역되지 않을 수 있습니다.

    ### **탭별 특징**
    * 📊 **PPT 번역**: 원본 텍스트 줄 아래에 파란색 번역문이 추가됩니다. (표 내용 포함)
    * 📄 **PDF 번역**: 일반 강의노트용입니다. 텍스트 바로 아래에 번역문이 삽입됩니다.
    * 📝 **논문 번역**: 문단 단위로 분석하며, 레이아웃 보존을 위해 원문을 가리고 한국어를 덮어씌웁니다.
    
    """)

with st.sidebar:
    st.header("⚙️ 옵션 설정")

    # [복구] 계층형 학과 리스트 전체 반영
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

    selected_dept = st.selectbox("2. 세부 전공 선택", dept_map[category])

    is_tech = category == "이과 (Science & Engineering)" and any(
        x in selected_dept for x in ["Computer", "Data", "AI", "Electrical"])

    st.divider()
    if st.button("🧹 번역 캐시 초기화"):
        st.session_state['translation_cache'] = {}
        st.success("캐시가 초기화되었습니다.")

tab1, tab2, tab3 = st.tabs(["📊 PPT 번역", "📄 PDF 번역", "📝 논문 번역"])


def run_translation(uploaded_file, mode):
    if uploaded_file and st.button(f"🚀 {mode} 번역 시작"):
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
            tmp_in.write(uploaded_file.getvalue())
            in_path = tmp_in.name
        out_path = os.path.join(tempfile.gettempdir(), f"translated_{uploaded_file.name}")
        try:
            with st.spinner(f"{selected_dept} 전문가 모드로 번역 중..."):
                # [수정] 인자 개수를 3개로 완벽히 수정 (in_path, out_path, selected_dept)
                if mode == "PPTX":
                    process_pptx(in_path, out_path, selected_dept)
                elif mode == "PDF":
                    process_pdf(in_path, out_path, selected_dept)
                elif mode == "PAPER":
                    process_paper(in_path, out_path, selected_dept)
            st.success("✅ 번역 완료!")
            with open(out_path, "rb") as f:
                st.download_button("💾 결과 다운로드", f, file_name=f"translated_{uploaded_file.name}")
        except Exception as e: st.error(f"오류 발생: {e}")
        finally:
            if os.path.exists(in_path): os.remove(in_path)

with tab1: run_translation(st.file_uploader("PPTX 업로드 (50p 이내)", type="pptx", key="p1"), "PPTX")
with tab2: run_translation(st.file_uploader("PDF 업로드 (50p 이내)", type="pdf", key="p2"), "PDF")
with tab3: run_translation(st.file_uploader("논문 PDF 업로드 (50p 이내)", type="pdf", key="p3"), "PAPER")

st.divider()
st.caption("Powered by Llama3 & PyMuPDF | EduTrans Project")