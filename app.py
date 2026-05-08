import streamlit as st
import fitz  # PyMuPDF
import os
import re
import json
import unicodedata
import tempfile
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from langchain_ollama import OllamaLLM
import platform
from glossary import DEFAULT_GLOSSARY

# --- [1. 초기 설정] ---
st.set_page_config(page_title="TransSlide AI - 로컬 전공 번역기", layout="wide", page_icon="🎓")

USER_GLOSSARY_PATH = "user_glossary.json"


def load_user_glossary():
    if os.path.exists(USER_GLOSSARY_PATH):
        try:
            with open(USER_GLOSSARY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_user_glossary(data):
    with open(USER_GLOSSARY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_merged_glossary(dept, user_glossary):
    """기본 용어 사전 위에 사용자 용어를 덮어써서 반환 (사용자 우선)"""
    base = dict(DEFAULT_GLOSSARY.get(dept, {}))
    base.update(user_glossary.get(dept, {}))
    return base


# 세션 상태 초기화
if "translation_cache" not in st.session_state:
    st.session_state["translation_cache"] = {}
if "detected_dept" not in st.session_state:
    st.session_state["detected_dept"] = None
if "user_glossary" not in st.session_state:
    st.session_state["user_glossary"] = load_user_glossary()


# 운영체제별 기본 폰트 경로 설정
def get_system_font():
    os_name = platform.system()
    if os_name == "Windows":
        return "C:/Windows/Fonts/malgun.ttf", "Malgun Gothic"
    elif os_name == "Darwin":
        return "/System/Library/Fonts/Supplemental/AppleGothic.ttf", "AppleGothic"
    else:
        return "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "NanumGothic"


FONT_FILE_PATH, FONT_NAME = get_system_font()


# --- [2. 사이드바 UI] ---
with st.sidebar:
    st.header("⚙️ 엔진 설정")
    selected_model = st.selectbox(
        "사용할 AI 모델 선택",
        ["phi3", "llama3"],
        index=0,
        help="저사양(8GB RAM)은 phi3를, 고사양(GPU 8GB+)은 llama3를 권장합니다."
    )

    llm = OllamaLLM(model=selected_model, temperature=0, num_predict=150)

    st.divider()
    st.header("🏫 전공 및 과목 설정")

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

    display_dept = st.session_state["detected_dept"] if (
        auto_detect and st.session_state["detected_dept"]
    ) else manual_dept
    st.info(f"📍 현재 적용 문맥: **{display_dept}**")

    # ── 용어 사전 편집 UI ──────────────────────────
    st.divider()
    st.header("📚 용어 사전 편집")
    st.caption(f"현재 전공: **{manual_dept}**")

    # 기본 용어 사전 보기
    with st.expander("기본 용어 사전 보기"):
        default_terms = DEFAULT_GLOSSARY.get(manual_dept, {})
        if default_terms:
            for eng, kor in default_terms.items():
                st.markdown(f"- **{eng}** → {kor}")
        else:
            st.caption("이 전공의 기본 용어가 아직 없습니다.")

    # 사용자 커스텀 용어 추가
    with st.expander("✏️ 내 용어 추가 / 수정"):
        with st.form("add_term_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_eng = st.text_input("영어 용어", placeholder="e.g. Gradient Descent")
            with col2:
                new_kor = st.text_input("한국어 번역", placeholder="e.g. 경사 하강법")
            submitted = st.form_submit_button("➕ 추가")
            if submitted and new_eng.strip() and new_kor.strip():
                dept_key = manual_dept
                if dept_key not in st.session_state["user_glossary"]:
                    st.session_state["user_glossary"][dept_key] = {}
                st.session_state["user_glossary"][dept_key][new_eng.strip()] = new_kor.strip()
                save_user_glossary(st.session_state["user_glossary"])
                st.success(f"추가됨: {new_eng.strip()} → {new_kor.strip()}")

    # 사용자 커스텀 용어 목록 & 삭제
    user_dept_terms = st.session_state["user_glossary"].get(manual_dept, {})
    if user_dept_terms:
        with st.expander(f"내 커스텀 용어 목록 ({len(user_dept_terms)}개)"):
            to_delete = []
            for eng, kor in user_dept_terms.items():
                col_t, col_d = st.columns([4, 1])
                with col_t:
                    st.markdown(f"**{eng}** → {kor}")
                with col_d:
                    if st.button("🗑️", key=f"del_{eng}"):
                        to_delete.append(eng)
            for key in to_delete:
                del st.session_state["user_glossary"][manual_dept][key]
                save_user_glossary(st.session_state["user_glossary"])
                st.rerun()

    # JSON 내보내기 / 가져오기
    with st.expander("📤 용어 사전 내보내기 / 가져오기"):
        export_data = json.dumps(st.session_state["user_glossary"], ensure_ascii=False, indent=2)
        st.download_button(
            "💾 내 용어 사전 다운로드 (JSON)",
            data=export_data,
            file_name="my_glossary.json",
            mime="application/json"
        )
        uploaded_glossary = st.file_uploader("JSON 용어 사전 불러오기", type="json", key="glossary_upload")
        if uploaded_glossary:
            try:
                imported = json.loads(uploaded_glossary.read().decode("utf-8"))
                for dept, terms in imported.items():
                    if dept not in st.session_state["user_glossary"]:
                        st.session_state["user_glossary"][dept] = {}
                    st.session_state["user_glossary"][dept].update(terms)
                save_user_glossary(st.session_state["user_glossary"])
                st.success("용어 사전을 성공적으로 가져왔습니다.")
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

    st.divider()
    if st.button("🧹 번역 캐시 초기화"):
        st.session_state["translation_cache"] = {}
        st.session_state["detected_dept"] = None
        st.success("캐시가 초기화되었습니다.")


# --- [3. 핵심 유틸리티] ---

def normalize_for_cache(text):
    return re.sub(r"\s+", " ", text.lower().strip())


def clean_text_logic(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("-\n", "").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def is_english_content(text):
    return any(c.isalpha() for c in text)


def detect_major_from_text(text):
    if not text.strip():
        return "General"
    prompt = (
        f"Analyze this text from a lecture slide and identify the academic major. "
        f"Answer with ONLY the name of the major in English.\n\nText: {text[:500]}\nMajor:"
    )
    try:
        return str(llm.invoke(prompt)).strip()
    except Exception:
        return "General"


def glossary_exact_match(text, glossary):
    """텍스트 전체 또는 대소문자 무관으로 용어 사전 직접 매칭"""
    stripped = text.strip()
    if stripped in glossary:
        return glossary[stripped]
    lower = stripped.lower()
    for k, v in glossary.items():
        if k.lower() == lower:
            return v
    return None


def build_glossary_hint(glossary, model):
    """모델별 glossary hint 문자열 생성 (용어 수를 30개로 제한해 프롬프트 과부하 방지)"""
    if not glossary:
        return ""
    items = list(glossary.items())[:30]
    if model == "llama3":
        pairs = ", ".join(f"{k}={v}" for k, v in items)
        return f"[Term mappings: {pairs}]"
    else:
        pairs = ", ".join(f"{k}->{v}" for k, v in items)
        return pairs


def post_process(translated, original):
    """LLM 출력 공통 후처리"""
    # 모델이 붙이는 접두어 패턴 제거 (강의:, 번역:, Korean: 등)
    trash_phrases = [
        r"^here is the translation:?",
        r"^translated text:?",
        r"^korean translation:?",
        r"^번역\s*:",
        r"^결과\s*:",
        r"^해석\s*:",
        r"^output\s*:",
        r"^korean\s*:",
        r"^강의\s*:",       # llama3 few-shot 오염 패턴
        r"^강의\s+\d+\s*:", # "강의 01:" 형태
        r"^translation\s*:",
    ]
    for phrase in trash_phrases:
        translated = re.sub(phrase, "", translated, flags=re.IGNORECASE).strip()

    # 키릴 문자 등 비정상 유니코드 블록 제거
    translated = re.sub(r"[^가-힣 -~ -ɏ　-〿().,!?:/\-\d]", "", translated).strip()

    # 앞뒤 따옴표 제거
    translated = re.sub(r'^["\' ]+|["\' ]+$', "", translated).strip()

    # 첫 줄만 사용 (llama3가 설명을 여러 줄 추가하는 경우 방지)
    lines = [l.strip() for l in translated.split("\n") if l.strip()]
    if lines:
        translated = lines[0] if len(lines[0]) > 1 else " ".join(lines[:2])

    # 번역 결과가 원문과 동일하거나 비어있으면 빈 문자열 반환
    if not translated or translated.lower() == original.lower():
        return ""

    return translated


def translate_single(text, department):
    cleaned = clean_text_logic(text)
    if len(cleaned) < 1:
        return text

    # 1. 캐시 확인
    norm_key = normalize_for_cache(cleaned)
    if norm_key in st.session_state["translation_cache"]:
        return st.session_state["translation_cache"][norm_key]

    # 2. 기본 용어 + 사용자 용어 병합 (사용자 용어 우선)
    glossary = get_merged_glossary(department, st.session_state["user_glossary"])

    # 3. 짧은 텍스트(6단어 이하)는 용어 사전 직접 매칭 우선 시도
    word_count = len(cleaned.split())
    if word_count <= 6:
        exact = glossary_exact_match(cleaned, glossary)
        if exact:
            st.session_state["translation_cache"][norm_key] = exact
            return exact

    # 4. glossary hint 생성
    glossary_hint = build_glossary_hint(glossary, selected_model)

    # 5. 모델별 프롬프트 분기
    if selected_model == "llama3":
        prompt = (
            f"You are a professional Korean translator specializing in {department}.\n"
            f"Translate the English text below into natural Korean.\n"
            f"Rules:\n"
            f"- Output ONLY the Korean translation. No explanations, no prefixes.\n"
            f"- Do NOT output 'Korean:', '번역:', '강의:' or any label before the translation.\n"
            f"{glossary_hint}\n\n"
            f"English: {cleaned}\n"
            f"Korean translation:"
        )
        stop_param = ["\nEnglish:", "\n\n"]
    else:
        # Phi-3: 영어 지시문으로 변경 (한국어 지시문이 혼란 유발)
        prompt = (
            f"You are a Korean translator for {department} academic content.\n"
            f"Translate the text below into Korean. Output ONLY Korean text.\n"
            f"Do NOT repeat the input. Do NOT add English. Do NOT add explanations.\n"
            f"Term guide: {glossary_hint}\n\n"
            f"Text to translate: {cleaned}\n"
            f"Korean:"
        )
        stop_param = ["\nText", "\nTerm", "English:", "\n\n"]

    try:
        translated = str(llm.invoke(prompt, stop=stop_param)).strip()
        translated = post_process(translated, cleaned)

        if not translated:
            return ""

        st.session_state["translation_cache"][norm_key] = translated
        return translated

    except Exception as e:
        st.error(f"Ollama 연결 확인 필요: {e}")
        return text


# --- [4. 문서 처리 함수] ---

def process_pptx(input_path, output_path, dept, auto_detect_flag):
    prs = Presentation(input_path)
    total_slides = len(prs.slides)
    progress_bar = st.progress(0)
    status_text = st.empty()

    if auto_detect_flag and total_slides > 0:
        first_text = ""
        for shape in prs.slides[0].shapes:
            if hasattr(shape, "text"):
                first_text += shape.text + " "
        st.session_state["detected_dept"] = detect_major_from_text(first_text)
        dept = st.session_state["detected_dept"]

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
                        run.font.name = FONT_NAME
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0, 102, 204)
        progress_bar.progress((i + 1) / total_slides)

    prs.save(output_path)
    status_text.text("✅ PPT 번역 완료!")


def process_pdf(input_path, output_path, dept, auto_detect_flag):
    doc = fitz.open(input_path)
    total_pages = len(doc)
    progress_bar = st.progress(0)
    status_text = st.empty()

    if auto_detect_flag and total_pages > 0:
        status_text.text("🧐 첫 페이지 분석 중... (전공 감지)")
        first_page = doc[0]
        first_text = " ".join([b[4] for b in first_page.get_text("blocks") if b[4].strip()])
        if first_text:
            st.session_state["detected_dept"] = detect_major_from_text(first_text)
            dept = st.session_state["detected_dept"]

    for i, page in enumerate(doc):
        status_text.text(f"📄 페이지 {i + 1}/{total_pages} 번역 중... (전공: {dept})")
        blocks = page.get_text("blocks")
        page_height = page.rect.height

        for b in blocks:
            raw_text = b[4].strip()
            if len(raw_text) < 3 or not is_english_content(raw_text):
                continue

            cleaned_text = raw_text.replace("\n", " ").strip()
            translated = translate_single(cleaned_text, dept)

            if translated and translated != cleaned_text:
                insert_x = b[0]
                insert_y = b[3] + 7

                # 페이지 하단을 벗어나지 않도록 보정
                if insert_y > page_height - 10:
                    continue

                try:
                    page.insert_text(
                        (insert_x, insert_y),
                        translated,
                        fontname="ko",
                        fontfile=FONT_FILE_PATH,
                        fontsize=8,
                        color=(0, 0.4, 0.8)
                    )
                except Exception:
                    continue

        progress_bar.progress((i + 1) / total_pages)

    doc.save(output_path)
    doc.close()
    status_text.text(f"✅ PDF 번역 완료! (적용 전공: {dept})")


# --- [5. 메인 UI] ---
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
    4. **용어 사전:** 사이드바에서 전공별 커스텀 용어를 추가·삭제하고 JSON으로 저장할 수 있습니다.
    5. **보안:** 모든 데이터는 본인 PC 내에서만 처리되어 안전합니다.
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
                        process_pdf(in_path, out_path, manual_dept, auto_detect)
                st.success("✅ 처리가 완료되었습니다!")
                with open(out_path, "rb") as f:
                    st.download_button("💾 결과 다운로드", f, file_name=f"translated_{uploaded_file.name}")
            except Exception as e:
                st.error(f"오류 발생: {e}")
            finally:
                if os.path.exists(in_path):
                    os.remove(in_path)


with tab1:
    run_translation(st.file_uploader("PPTX 업로드", type="pptx", key="p1"), "PPTX")
with tab2:
    run_translation(st.file_uploader("PDF 업로드", type="pdf", key="p2"), "PDF")

st.divider()
st.markdown("""
    <div style="text-align: center; color: gray; font-size: 0.8rem;">
        <p><b>Built with Meta Llama 3</b> | Powered by Microsoft Phi-3</p>
        <p>Meta Llama 3 is licensed under the Meta Llama 3 Community License. Copyright © Meta Platforms, Inc.</p>
        <p>Phi-3 is licensed under the MIT License. Copyright © Microsoft Corporation.</p>
    </div>
    """, unsafe_allow_html=True)
