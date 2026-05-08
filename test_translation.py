"""
번역 로직 독립 테스트 스크립트 (Streamlit 없이 실행)
실제 PPTX에서 추출한 텍스트로 모델별 결과를 비교합니다.
"""
import re
import unicodedata
from langchain_ollama import OllamaLLM
from glossary import DEFAULT_GLOSSARY

# ── 테스트할 모델 ──────────────────────────────────────
MODELS = {
    "qwen2.5:3b":  {"family": "qwen",  "num_predict": 150, "stop": ["\nEnglish:", "\n"]},
    "llama3.2:3b": {"family": "llama", "num_predict": 120, "stop": ["\nEnglish:", "\n"]},
    "llama3":      {"family": "llama", "num_predict": 180, "stop": ["\nEnglish:", "\n\n"]},
}

# ── 실제 PPTX에서 뽑은 테스트 문장 ────────────────────
TEST_CASES = [
    # (원문, 전공)
    ("Introduction to Data Science",                                                    "Data Science"),
    ("Lecture 01: Core Concepts and Workflow",                                          "Data Science"),
    ("What is Data Science?",                                                           "Data Science"),
    ("A multi-disciplinary field that uses scientific methods, processes, algorithms, "
     "and systems to extract knowledge and insights from structured and unstructured data.", "Data Science"),
    ("Key Components:",                                                                 "Data Science"),
    ("Statistics & Mathematics",                                                        "Data Science"),
    ("Domain Knowledge",                                                                "Data Science"),
    ("Exploratory Data Analysis (EDA)",                                                 "Data Science"),
    ("Model Training & Parameter Tuning",                                               "Data Science"),
    ("Standard Precautions and Infection Control",                                      "Nursing"),
    ("Personal Protective Equipment (PPE): Proper sequence for donning gloves.",        "Nursing"),
    ("Aseptic Technique: Maintaining a sterile field during invasive procedures.",      "Nursing"),
]

# ── 유틸 함수 (app.py와 동일 로직) ─────────────────────

def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("-\n", "").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


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


def build_glossary_hint(glossary, text):
    text_lower = text.lower()
    matched = {k: v for k, v in glossary.items() if k.lower() in text_lower}
    if not matched:
        return ""
    items = list(matched.items())[:6]
    pairs = ", ".join(f"{k}={v}" for k, v in items)
    return f"[Terms: {pairs}]"


def post_process(translated, original):
    translated = re.sub(r"<think>.*?</think>", "", translated, flags=re.DOTALL).strip()
    trash = [
        r"^here is the translation:?", r"^translated text:?", r"^korean translation:?",
        r"^번역\s*:", r"^결과\s*:", r"^output\s*:", r"^korean\s*:",
        r"^강의\s*:", r"^강의\s+\d+\s*:", r"^translation\s*:", r"^/no_think",
    ]
    for p in trash:
        translated = re.sub(p, "", translated, flags=re.IGNORECASE).strip()
    translated = re.sub(r"[^가-힣 -~ -ɏ　-〿().,!?:/\-\d]", "", translated).strip()
    translated = re.sub(r'^["\' ]+|["\' ]+$', "", translated).strip()
    lines = [l.strip() for l in translated.split("\n") if l.strip()]
    if lines:
        translated = lines[0] if len(lines[0]) > 1 else " ".join(lines[:2])
    if not translated or translated.lower() == original.lower():
        return ""
    return translated


def translate(text, dept, model_name, model_cfg, llm):
    cleaned = clean_text(text)
    glossary = get_glossary(dept)

    if len(cleaned.split()) <= 6:
        exact = glossary_exact_match(cleaned, glossary)
        if exact:
            return exact, "(glossary 직접 매칭)"

    family = model_cfg["family"]
    hint = build_glossary_hint(glossary, cleaned)
    stop = model_cfg["stop"]

    if family == "qwen":
        prompt = (
            f"You are a Korean translator for {dept} academic slides.\n"
            f"Translate the English text into Korean. ONE LINE only. No lists. No explanations.\n"
            f"{hint}\n\n"
            f"English: {cleaned}\n"
            f"Korean:"
        )
    else:
        prompt = (
            f"You are a Korean translator for {dept} academic slides.\n"
            f"Translate the English text into Korean. ONE SHORT LINE only. No lists. No explanations. No extra sentences.\n"
            f"{hint}\n\n"
            f"English: {cleaned}\n"
            f"Korean:"
        )

    raw = str(llm.invoke(prompt, stop=stop)).strip()
    result = post_process(raw, cleaned)
    return result, f"(hint: '{hint}' | raw: '{raw[:60]}...')" if len(raw) > 60 else f"(hint: '{hint}' | raw: '{raw}')"


# ── 실행 ───────────────────────────────────────────────

def run():
    print("=" * 70)
    print("  번역 테스트 — 모델별 결과 비교")
    print("=" * 70)

    results = {}

    for model_name, model_cfg in MODELS.items():
        print(f"\n{'─'*70}")
        print(f"  모델: {model_name}")
        print(f"{'─'*70}")

        try:
            llm = OllamaLLM(
                model=model_name,
                temperature=0,
                num_predict=model_cfg["num_predict"],
            )
            model_results = []
            for text, dept in TEST_CASES:
                result, debug = translate(text, dept, model_name, model_cfg, llm)
                model_results.append((text, dept, result))
                status = "✅" if result else "❌ (빈 출력)"
                print(f"  {status} [{dept[:12]:12}] {text[:45]:45}")
                print(f"         → {result or '(번역 없음)'}")
            results[model_name] = model_results
        except Exception as e:
            print(f"  ❌ 모델 오류: {e}")
            results[model_name] = []

    # ── 요약 비교표 ────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  요약 비교표")
    print(f"{'=' * 70}")

    model_names = list(MODELS.keys())
    for i, (text, dept) in enumerate(TEST_CASES):
        print(f"\n  원문: {text[:60]}")
        for mname in model_names:
            r = results.get(mname, [])
            val = r[i][2] if i < len(r) else "(오류)"
            print(f"    {mname:15}: {val or '(빈 출력)'}")

    print(f"\n{'=' * 70}")
    print("  테스트 완료")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run()
