"""PDF 번역 실행 스크립트 (코드 블록 주석, 한국어 스킵 포함)"""
import re
import unicodedata
import fitz
from langchain_ollama import OllamaLLM
from glossary import DEFAULT_GLOSSARY

MODEL_NAME = "qwen2.5:3b"
FONT_FILE  = "C:/Windows/Fonts/malgun.ttf"
INPUT_PDF  = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\haeun.pdf"
OUTPUT_PDF = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\translated_cs_lecture.pdf"
TEST_PAGES = None  # None = 전체, 숫자 = 처음 N페이지

llm = OllamaLLM(model=MODEL_NAME, temperature=0, num_predict=150)
cache = {}

CODE_PATTERNS = [
    r'#include', r'\bint\s+\w+\s*\(', r'\bvoid\s+\w+\s*\(',
    r'\bfor\s*\(', r'\bwhile\s*\(', r'\breturn\s+',
    r'printf\s*\(', r'scanf\s*\(', r'^\s*//', r'[{};]$',
    r'->\w+', r'0x[0-9a-fA-F]+',
    r'\bmov\w*\s+%', r'\bpush\b', r'\bpop\b',
    r'\.text\b', r'\.data\b', r'\bcall\b\s+\w+',
    r'^\s*\w+:\s*$',  # 어셈블리 레이블
]


def is_code_block(text):
    lines = [l for l in text.split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    hits = sum(1 for line in lines if any(re.search(p, line) for p in CODE_PATTERNS))
    return hits / len(lines) > 0.35


def is_english(text):
    ascii_alpha = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    korean = sum(1 for c in text if '가' <= c <= '힣')
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0 or ascii_alpha == 0:
        return False
    return korean / total_alpha < 0.3


def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text.replace("-\n", "").replace("\n", " ")).strip()


def glossary_exact_match(text, glossary):
    stripped = text.strip().rstrip(":")
    if stripped in glossary:
        return glossary[stripped]
    lower = stripped.lower()
    for k, v in glossary.items():
        if k.lower() == lower:
            return v
    return None


def build_hint(glossary, text):
    text_lower = text.lower()
    matched = {k: v for k, v in glossary.items() if k.lower() in text_lower}
    if not matched:
        return ""
    pairs = ", ".join(f"{k}={v}" for k, v in list(matched.items())[:6])
    return f"[Terms: {pairs}]"


def post_process(translated, original):
    translated = re.sub(r"<think>.*?</think>", "", translated, flags=re.DOTALL).strip()
    for p in [r"^korean translation:?", r"^번역\s*:", r"^korean\s*:", r"^translation\s*:", r"^output\s*:"]:
        translated = re.sub(p, "", translated, flags=re.IGNORECASE).strip()
    translated = re.sub(r"[^가-힣 -~ -ɏ　-〿().,!?:/\-\d]", "", translated).strip()
    translated = re.sub(r'^["\' ]+|["\' ]+$', "", translated).strip()
    lines = [l.strip() for l in translated.split("\n") if l.strip()]
    if lines:
        translated = lines[0] if len(lines[0]) > 1 else " ".join(lines[:2])
    if not translated or translated.lower() == original.lower():
        return ""
    return translated


def translate(text, dept):
    cleaned = clean_text(text)
    if len(cleaned) < 2 or not is_english(cleaned):
        return ""
    key = re.sub(r"\s+", " ", cleaned.lower().strip())
    if key in cache:
        return cache[key]
    glossary = dict(DEFAULT_GLOSSARY.get(dept, {}))
    if len(cleaned.split()) <= 6:
        exact = glossary_exact_match(cleaned, glossary)
        if exact:
            cache[key] = exact
            return exact
    hint = build_hint(glossary, cleaned)
    prompt = (
        f"You are a Korean translator for {dept} academic slides.\n"
        f"Translate the English text into Korean. ONE LINE only. No lists. No explanations.\n"
        f"{hint}\n\n"
        f"English: {cleaned}\nKorean:"
    )
    raw = str(llm.invoke(prompt, stop=["\nEnglish:", "\n"])).strip()
    result = post_process(raw, cleaned)
    cache[key] = result
    return result


def comment_code(code_text):
    """코드 블록 한 줄 한국어 주석 생성"""
    key = "CODE:" + re.sub(r"\s+", " ", code_text[:200].strip())
    if key in cache:
        return cache[key]
    prompt = (
        f"Read this code and describe what it does in ONE short Korean sentence.\n"
        f"Output format: # [한국어 설명]\n"
        f"Only output the comment line. No extra text.\n\n"
        f"Code:\n{code_text[:400]}\nComment:"
    )
    raw = str(llm.invoke(prompt, stop=["\n"])).strip()
    # # 접두어 보장
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r'^["\' ]+|["\' ]+$', "", raw).strip()
    if not raw.startswith("#"):
        raw = "# " + raw
    # 한국어가 있으면 유효
    if any('가' <= c <= '힣' for c in raw):
        cache[key] = raw
        return raw
    cache[key] = ""
    return ""


def detect_dept(doc, fallback="Computer Science"):
    first_text = " ".join([b[4] for b in doc[0].get_text("blocks") if b[4].strip()])
    if not first_text.strip():
        return fallback
    prompt = (
        f"Read this university lecture slide text and identify the academic major.\n"
        f"Reply with ONLY the major name in English (e.g. 'Computer Science', 'Data Science').\n"
        f"Text: {first_text[:500]}\nMajor:"
    )
    try:
        result = str(llm.invoke(prompt, stop=["\n"])).strip()
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip().split("\n")[0]
        if not result or result.lower() in ("general", "unknown", "none"):
            return fallback
        return result
    except Exception:
        return fallback


def run():
    doc = fitz.open(INPUT_PDF)
    total = len(doc)
    limit = TEST_PAGES if TEST_PAGES else total
    print(f"총 {total}페이지 중 {limit}페이지 번역")

    dept = detect_dept(doc)
    print(f"감지된 전공: {dept}\n")

    ok = skip_kor = skip_code = fail = 0

    for i in range(limit):
        page = doc[i]
        blocks = page.get_text("blocks")
        page_height = page.rect.height
        page_ok = page_code = 0

        for b in blocks:
            raw = b[4].strip()
            if len(raw) < 3:
                continue
            if not is_english(raw):
                skip_kor += 1
                continue
            if is_code_block(raw):
                result = comment_code(raw)
                page_code += 1
                skip_code += 1
            else:
                cleaned = raw.replace("\n", " ").strip()
                result = translate(cleaned, dept)
            if result:
                insert_y = b[3] + 7
                if insert_y > page_height - 10:
                    continue
                try:
                    page.insert_text(
                        (b[0], insert_y), result,
                        fontname="ko", fontfile=FONT_FILE,
                        fontsize=8, color=(0, 0.4, 0.8)
                    )
                    ok += 1
                    page_ok += 1
                except Exception:
                    fail += 1
            else:
                fail += 1

        code_info = f" (코드주석 {page_code}건)" if page_code else ""
        print(f"  p{i+1:03d}/{limit} 번역 {page_ok}건{code_info}")

    doc.save(OUTPUT_PDF)
    doc.close()
    print(f"\n저장: {OUTPUT_PDF}")
    print(f"결과: 번역={ok} | 코드주석={skip_code} | 한국어스킵={skip_kor} | 실패={fail}")


if __name__ == "__main__":
    run()
