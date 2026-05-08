"""
PDF 번역 파이프라인 테스트
1. DS 강의 PDF 실제 번역 테스트 (처음 5페이지)
2. Computer Science 샘플 PDF 생성 후 번역 테스트
"""
import re
import os
import unicodedata
import tempfile
import fitz
from fpdf import FPDF
from langchain_ollama import OllamaLLM
from glossary import DEFAULT_GLOSSARY

# ── 설정 ───────────────────────────────────────────────
MODEL_NAME = "qwen2.5:3b"
MODEL_CFG  = {"num_predict": 150, "stop": ["\nEnglish:", "\n"], "family": "qwen"}
FONT_FILE  = "C:/Windows/Fonts/malgun.ttf"
DS_PDF     = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\(DS) w2 Intoduction to Data Science.pdf"
CS_PDF_OUT = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\(CS) sample_Computer_Science.pdf"
DS_OUT     = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\translated_DS_w2_test.pdf"
CS_OUT     = r"C:\Users\seoyeon\PycharmProjects\my_translator\Test Files\translated_CS_sample.pdf"
MAX_PAGES  = 15  # DS PDF 테스트 범위

llm = OllamaLLM(model=MODEL_NAME, temperature=0, num_predict=MODEL_CFG["num_predict"])
cache = {}


# ── 유틸 ───────────────────────────────────────────────

def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text.replace("-\n", "").replace("\n", " ")).strip()


def is_english(text):
    ascii_alpha = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    korean = sum(1 for c in text if '가' <= c <= '힣')
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0 or ascii_alpha == 0:
        return False
    return korean / total_alpha < 0.3


def get_glossary(dept):
    return dict(DEFAULT_GLOSSARY.get(dept, {}))


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
    glossary = get_glossary(dept)
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
    raw = str(llm.invoke(prompt, stop=MODEL_CFG["stop"])).strip()
    result = post_process(raw, cleaned)
    cache[key] = result
    return result


def detect_dept(text, fallback):
    if not text.strip():
        return fallback
    prompt = (
        f"Read this university lecture slide text and identify the academic major.\n"
        f"Reply with ONLY the major name in English (e.g. 'Data Science', 'Computer Science').\n"
        f"Text: {text[:500]}\nMajor:"
    )
    try:
        result = str(llm.invoke(prompt, stop=["\n"])).strip()
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip().split("\n")[0]
        if not result or result.lower() in ("general", "unknown", "none"):
            return fallback
        return result
    except Exception:
        return fallback


# ── CS 샘플 PDF 생성 ────────────────────────────────────

def make_cs_pdf(path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    slides = [
        {
            "title": "Introduction to Computer Science",
            "subtitle": "CS101 - Fundamentals of Computing",
            "body": []
        },
        {
            "title": "What is Computer Science?",
            "body": [
                "The study of computation, algorithms, and data structures.",
                "Covers both theoretical foundations and practical applications.",
                "Key areas: Software Engineering, Artificial Intelligence, Networking.",
            ]
        },
        {
            "title": "Core Concepts",
            "body": [
                "Algorithm: A step-by-step procedure for solving a problem.",
                "Data Structure: A way of organizing and storing data.",
                "Time Complexity: Measure of algorithm efficiency (Big-O notation).",
                "Recursion: A function that calls itself to solve sub-problems.",
            ]
        },
        {
            "title": "Programming Paradigms",
            "body": [
                "Object-Oriented Programming (OOP): Encapsulation, Inheritance, Polymorphism.",
                "Functional Programming: Pure functions, immutability, higher-order functions.",
                "Procedural Programming: Sequential execution with procedures and loops.",
            ]
        },
        {
            "title": "Operating Systems",
            "body": [
                "Manages hardware resources and provides services to applications.",
                "Key concepts: Process Management, Memory Management, File Systems.",
                "Scheduling algorithms: FIFO, Round Robin, Priority Scheduling.",
                "Virtual Memory: Allows processes to use more memory than physically available.",
            ]
        },
        {
            "title": "Database Systems",
            "body": [
                "Relational Database: Data stored in tables with rows and columns.",
                "SQL (Structured Query Language): Used to query and manipulate data.",
                "Normalization: Organizing data to reduce redundancy.",
                "Transactions: ACID properties — Atomicity, Consistency, Isolation, Durability.",
            ]
        },
        {
            "title": "Computer Networks",
            "body": [
                "OSI Model: 7-layer architecture for network communication.",
                "TCP/IP Protocol Suite: Foundation of the modern Internet.",
                "HTTP/HTTPS: Protocol for web communication.",
                "DNS (Domain Name System): Resolves domain names to IP addresses.",
            ]
        },
    ]

    for slide in slides:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(30, 80, 160)
        pdf.cell(0, 12, slide["title"], ln=True)
        pdf.ln(2)

        if "subtitle" in slide:
            pdf.set_font("Helvetica", "I", 13)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 8, slide["subtitle"], ln=True)
            pdf.ln(4)

        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(30, 30, 30)
        for line in slide.get("body", []):
            pdf.multi_cell(0, 8, f"- {line}")
            pdf.ln(1)

    pdf.output(path)
    print(f"CS 샘플 PDF 생성 완료: {path}")


# ── PDF 번역 함수 ───────────────────────────────────────

def translate_pdf(input_path, output_path, dept, max_pages=None):
    doc = fitz.open(input_path)
    total = len(doc)
    if max_pages:
        total = min(total, max_pages)

    # 전공 자동 감지
    first_text = " ".join([b[4] for b in doc[0].get_text("blocks") if b[4].strip()])
    detected = detect_dept(first_text, dept)
    print(f"  감지된 전공: {detected}")

    ok, skip, fail = 0, 0, 0

    for i in range(total):
        page = doc[i]
        blocks = page.get_text("blocks")
        page_height = page.rect.height
        print(f"  페이지 {i+1}/{total} 번역 중...", end=" ", flush=True)
        page_ok = 0

        for b in blocks:
            raw = b[4].strip()
            if len(raw) < 3 or not is_english(raw):
                skip += 1
                continue
            cleaned = raw.replace("\n", " ").strip()
            result = translate(cleaned, detected)
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

        print(f"번역 {page_ok}건")

    doc.save(output_path)
    doc.close()
    print(f"  저장: {output_path}")
    print(f"  결과: 성공={ok}, 스킵={skip}, 실패={fail}\n")


# ── 실행 ───────────────────────────────────────────────

print("=" * 60)
print("  [1] DS 강의 PDF 번역 테스트 (처음 5페이지)")
print("=" * 60)
translate_pdf(DS_PDF, DS_OUT, "Data Science", max_pages=MAX_PAGES)

print("=" * 60)
print("  [2] Computer Science 샘플 PDF 생성")
print("=" * 60)
make_cs_pdf(CS_PDF_OUT)

print("=" * 60)
print("  [3] Computer Science 샘플 PDF 번역")
print("=" * 60)
translate_pdf(CS_PDF_OUT, CS_OUT, "Computer Science")

print("=" * 60)
print("  테스트 완료")
print(f"  DS 번역 결과  : {DS_OUT}")
print(f"  CS 번역 결과  : {CS_OUT}")
print("=" * 60)
