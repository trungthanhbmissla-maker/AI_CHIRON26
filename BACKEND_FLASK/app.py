import json
import os
import time
import traceback
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# ---------------------------
# 🔧 AI client setup
# ---------------------------
try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
except Exception:
    genai = None
    ResourceExhausted = Exception  # fallback

# ---------------------------
# ⚙️ Load environment
# ---------------------------
load_dotenv()
app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_FALLBACK", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if genai and GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        app.logger.info(f"✅ Google Generative AI configured (model={GEMINI_MODEL}).")
    except Exception as e:
        app.logger.error(f"❌ Failed to configure Gemini API: {e}")

# ---------------------------
# ⚙️ Global state
# ---------------------------
executor = ThreadPoolExecutor(max_workers=3)
quiz_cache = {}

# ---------------------------
# 🔁 Danh sách model fallback (2.x trở lên)
# ---------------------------
MODELS_TO_TRY = [
    GEMINI_MODEL,
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite-preview-09-2025",
    "gemini-2.5-flash-native-audio-preview-09-2025",
]

# ---------------------------
# 🧠 Sinh nội dung từ AI
# ---------------------------
def generate_text(prompt, retries=2):
    if genai is None:
        raise RuntimeError("Google generative AI client not available.")

    generation_config = {
        "temperature": 0.3,
        "top_p": 0.8,
        "max_output_tokens": 1600,
        "response_mime_type": "application/json",
    }

    for attempt in range(retries):
        for model_name in MODELS_TO_TRY:
            if "1.5" in model_name:
                continue  # ❌ Không dùng model 1.5 nữa

            try:
                app.logger.info(f"🔍 Trying model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=generation_config)

                text = ""
                if response and hasattr(response, "candidates") and response.candidates:
                    parts = getattr(response.candidates[0].content, "parts", [])
                    text = "".join(getattr(p, "text", "") for p in parts)

                if text.strip():
                    return text.strip()

            except ResourceExhausted:
                app.logger.warning(f"⚠️ Model {model_name} quota exhausted.")
                continue
            except Exception as e:
                app.logger.warning(f"⚠️ Model {model_name} failed: {e}")
                continue

        time.sleep(0.6)

    raise Exception("❌ All models failed or returned invalid data.")

# ---------------------------
# 🔍 Parse JSON an toàn
# ---------------------------
def safe_parse_json(text):
    def try_load(s):
        try:
            return json.loads(s)
        except Exception:
            return None

    if not text:
        return None

    try:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError("No JSON object found.")
        clean_text = json_match.group(0).strip()

        parsed = try_load(clean_text)
        if parsed:
            return parsed

        fix_text = (
            clean_text.replace("\n", " ")
            .replace("\r", "")
            .replace(", }", "}")
            .replace(",]", "]")
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("'", '"')
        )

        parsed = try_load(fix_text)
        if parsed:
            return parsed

        first, last = fix_text.find("{"), fix_text.rfind("}")
        if first != -1 and last != -1:
            parsed = try_load(fix_text[first:last + 1])
            if parsed:
                return parsed

        raise ValueError("Could not parse cleaned JSON.")
    except Exception as e:
        app.logger.warning(f"⚠️ JSON parse thất bại: {e}")
        return None

# ---------------------------
# 🔢 Chuẩn hóa ký hiệu
# ---------------------------
def normalize_math_symbols(text: str) -> str:
    import re

    if not text or not isinstance(text, str):
        return text

    # 1️⃣ Bỏ ký tự thoát LaTeX: \
    text = text.replace("\\", "")

    # 2️⃣ Chuẩn hóa sqrt hoặc √
    text = re.sub(r"sqrt\s*\{([^}]+)\}", r"√\1", text)
    text = re.sub(r"sqrt\s*\(([^)]+)\)", r"√\1", text)
    text = re.sub(r"√\s*\{([^}]+)\}", r"√\1", text)
    text = re.sub(r"√\s*\(([^)]+)\)", r"√\1", text)

    # 3️⃣ Lũy thừa (x^2 → x², x^3 → x³)
    text = re.sub(r"\^2\b", "²", text)
    text = re.sub(r"\^3\b", "³", text)
    text = re.sub(
        r"\^\{(\d)\}", 
        lambda m: "²" if m.group(1) == "2" else ("³" if m.group(1) == "3" else f"^{m.group(1)}"),
        text
    )

    # 4️⃣ Thay ký hiệu toán học phổ biến
    replacements = {
        "pi": "π",
        "<=": "≤",
        ">=": "≥",
        "!=": "≠",
        "->": "→",
        "<-": "←",
        "inf": "∞",
        "theta": "θ",
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "delta": "δ",
        "Omega": "Ω",
        "omega": "ω",
    }
    for k, v in replacements.items():
        text = re.sub(rf"\b{k}\b", v, text, flags=re.IGNORECASE)

    # 5️⃣ Hóa học: CH3COOH → CH₃COOH
    subscript_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    def chemical_subscripts(match):
        formula = match.group(0)
        # chỉ thay số sau chữ cái
        return re.sub(r"(?<=[A-Za-z])(\d+)", lambda m: m.group(1).translate(subscript_map), formula)

    text = re.sub(r"\b[A-Z][A-Za-z0-9()]*\b", chemical_subscripts, text)

    # 6️⃣ Xóa khoảng trắng thừa
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# ---------------------------
# 🧩 API sinh đề trắc nghiệm (bản có TTL + force_regen)
# ---------------------------
@app.route("/api/generate-quiz", methods=["POST"])
def api_generate_quiz():
    start_time = time.time()
    try:
        data = request.get_json(force=True)
        subject = data.get("subject", "")
        grade = str(data.get("grade", ""))
        topic = data.get("topic", "").strip()
        num_mcq = int(data.get("num_mcq", 10))
        num_tf = int(data.get("num_tf", 4))
        force_regen = bool(data.get("force_regen", False))

        CACHE_TTL = 120  # ⏱ 2 phút
        cache_key = json.dumps(
            {"subject": subject, "grade": grade, "topic": topic, "num_mcq": num_mcq, "num_tf": num_tf},
            sort_keys=True
        )

        # ⚡ Kiểm tra cache
        cached_entry = quiz_cache.get(cache_key)
        if (
            not force_regen
            and cached_entry
            and (time.time() - cached_entry["time"] < CACHE_TTL)
        ):
            app.logger.info("⚡ Trả đề từ cache RAM (hợp lệ trong 5 phút).")
            return jsonify(cached_entry["data"])

        # ---------------------------
        # PROMPT 1: MCQ
        # ---------------------------
        prompt_mcq = f"""
Chỉ trả về JSON hợp lệ, không markdown.
Tạo {num_mcq} câu hỏi trắc nghiệm nhiều lựa chọn (MCQ) cho học sinh:
- Môn học: {subject}
- Lớp: {grade}
- Chủ đề: {topic}

Định dạng:
{{
  "questions": [
    {{
      "type": "mcq",
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "A"
    }}
  ]
}}
"""

        # ---------------------------
        # PROMPT 2: True/False
        # ---------------------------
        prompt_tf = f"""
Chỉ trả về JSON hợp lệ, không markdown.
Tạo {num_tf} câu hỏi dạng Đúng/Sai cho học sinh:
- Môn học: {subject}
- Lớp: {grade}
- Chủ đề: {topic}

Định dạng:
{{
  "questions": [
    {{
      "type": "truefalse",
      "question": "...",
      "options": ["A. Đúng", "B. Sai"],
      "answer": "A"
    }}
  ]
}}
"""

        # 🧠 Sinh song song MCQ và True/False
        fut_mcq = executor.submit(generate_text, prompt_mcq)
        fut_tf = executor.submit(generate_text, prompt_tf)
        raw_mcq, raw_tf = fut_mcq.result(timeout=25), fut_tf.result(timeout=25)

        data_mcq = safe_parse_json(raw_mcq) or {"questions": []}
        data_tf = safe_parse_json(raw_tf) or {"questions": []}

        all_questions = data_mcq.get("questions", []) + data_tf.get("questions", [])
        expected_total = num_mcq + num_tf

        # 🔧 Nếu thiếu câu hỏi, sinh bổ sung
        if len(all_questions) < expected_total:
            missing = expected_total - len(all_questions)
            app.logger.warning(f"⚠️ Thiếu {missing} câu, sinh bổ sung.")
            prompt_fix = f"Tạo thêm {missing} câu hỏi cho {subject} lớp {grade} chủ đề {topic}, định dạng JSON như trước."
            extra = generate_text(prompt_fix)
            data_extra = safe_parse_json(extra)
            if data_extra and isinstance(data_extra, dict):
                all_questions += data_extra.get("questions", [])

        # 🔢 Chuẩn hóa ký hiệu toán học
        for q in all_questions:
            for field in ["question", "answer"]:
                if field in q:
                    q[field] = normalize_math_symbols(q[field])
            if "options" in q and isinstance(q["options"], list):
                q["options"] = [normalize_math_symbols(opt) for opt in q["options"]]

        result = {"questions": all_questions[:expected_total]}

        # 💾 Lưu cache cùng timestamp
        quiz_cache[cache_key] = {"data": result, "time": time.time()}

        elapsed = round((time.time() - start_time) * 1000)
        app.logger.info(f"✅ Sinh đề hoàn tất: {len(result['questions'])} câu ({elapsed} ms)")
        return jsonify(result)

    except Exception as e:
        app.logger.error(f"❌ Exception: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
    
# ---------------------------
# 🚀 Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
