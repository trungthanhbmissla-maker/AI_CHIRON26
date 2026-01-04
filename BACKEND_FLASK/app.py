from werkzeug.exceptions import MethodNotAllowed
import json
import os
import time
import traceback
import re
from flask import Flask, jsonify, request, make_response
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
# Explicit CORS config (allows all origins — fine for dev; tighten in production)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config["JSON_SORT_KEYS"] = False

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
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite-preview-09-2025",
    "gemini-2.5-flash-native-audio-preview-09-2025",
]

# ---------------------------
# Middleware: log request for debugging
# ---------------------------
@app.before_request
def log_request_info():
    try:
        app.logger.info("----- Incoming Request -----")
        app.logger.info(f"Remote Addr: {request.remote_addr}")
        app.logger.info(f"Method: {request.method} URL: {request.url}")
        headers = {k: v for k, v in request.headers.items()}
        app.logger.info(f"Headers: {headers}")
        # Avoid logging huge bodies but log content-type and length
        app.logger.info(f"Content-Type: {request.content_type} Content-Length: {request.content_length}")
    except Exception as e:
        app.logger.warning(f"Failed to log request info: {e}")

# Ensure preflight requests (OPTIONS) return 200 quickly
@app.route("/", methods=["OPTIONS"])
@app.route("/<path:anypath>", methods=["OPTIONS"])
def handle_options(anypath=None):
    resp = make_response()
    resp.status_code = 200
    return resp

# After-request to ensure proper CORS and allow headers (helps with proxies/CDN)
@app.after_request
def add_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept")
    response.headers.setdefault("Access-Control-Expose-Headers", "Content-Type, Authorization")
    return response

# Health check route
@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

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
    """
    Chuẩn hóa một chuỗi văn bản chứa các ký hiệu và công thức toán học,
    hóa học và vật lý về định dạng Unicode đẹp mắt.

    Args:
        text: Chuỗi văn bản đầu vào.

    Returns:
        Chuỗi văn bản đã được chuẩn hóa.
    """
    if not text or not isinstance(text, str):
        return text

    # --- 1. Từ điển chuyển đổi (Giữ nguyên như cũ) ---
    latex_unicode_map = {
        r'\\alpha': 'α', r'\\beta': 'β', r'\\gamma': 'γ', r'\\delta': 'δ', r'\\epsilon': 'ε',
        r'\\zeta': 'ζ', r'\\eta': 'η', r'\\theta': 'θ', r'\\iota': 'ι', r'\\kappa': 'κ',
        r'\\lambda': 'λ', r'\\mu': 'μ', r'\\nu': 'ν', r'\\xi': 'ξ', r'\\omicron': 'ο',
        r'\\pi': 'π', r'\\rho': 'ρ', r'\\sigma': 'σ', r'\\tau': 'τ', r'\\upsilon': 'υ',
        r'\\phi': 'φ', r'\\chi': 'χ', r'\\psi': 'ψ', r'\\omega': 'ω',
        r'\\Gamma': 'Γ', r'\\Delta': 'Δ', r'\\Theta': 'Θ', r'\\Lambda': 'Λ', r'\\Xi': 'Ξ',
        r'\\Pi': 'Π', r'\\Sigma': 'Σ', r'\\Upsilon': 'Υ', r'\\Phi': 'Φ', r'\\Psi': 'Ψ',
        r'\\Omega': 'Ω',
        r'\\pm': '±', r'\\times': '×', r'\\div': '÷', r'\\cdot': '⋅', r'\\neq': '≠',
        r'\\leq': '≤', r'\\geq': '≥', r'\\approx': '≈', r'\\equiv': '≡', r'\\in': '∈',
        r'\\notin': '∉', r'\\subset': '⊂', r'\\supset': '⊃', r'\\subseteq': '⊆',
        r'\\supseteq': '⊇', r'\\sum': '∑', r'\\int': '∫', r'\\partial': '∂',
        r'\\nabla': '∇', r'\\infty': '∞', r'\\forall': '∀', r'\\exists': '∃',
        r'\\angle': '∠', r'\\perp': '⊥',
        r'\\rightarrow': '→', r'\\leftarrow': '←', r'\\leftrightarrow': '↔',
        r'\\Rightarrow': '⇒', r'\\Leftarrow': '⇐', r'\\Leftrightarrow': '⇔',
        r'\\uparrow': '↑', r'\\downarrow': '↓',
        r'\\ldots': '…', r'\\cdots': '⋯', r'\\vdots': '⋮', r'\\ddots': '⋱',
        r'\\circ': '°',
    }
    keyword_map = {
        r'sqrt': '√', 'inf': '∞',
    }
    operator_map = {
        '>=': '≥', '<=': '≤', '!=': '≠', '->': '→', '<-': '←', '<=>': '⇔'
    }
    superscript_map = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
    subscript_map = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")

    # --- 2. Thực hiện chuyển đổi ---
    # Thay thế các toán tử đặc biệt
    for op, uni in operator_map.items():
        text = text.replace(op, uni)
    # Thay thế các lệnh LaTeX
    for latex, uni in latex_unicode_map.items():
        text = re.sub(latex + r'\b', uni, text)
    # Thay thế các từ khóa
    for keyword, uni in keyword_map.items():
        text = re.sub(r'\b' + keyword + r'\b', uni, text, flags=re.IGNORECASE)
    # Thay thế ký hiệu độ dạng `^o`
    text = re.sub(r'\^o\b', '°', text)

    # --- 3. Xử lý các cấu trúc phức tạp hơn bằng Regex ---

    # CẢI TIẾN: Chuẩn hóa căn bậc hai và thêm ngoặc để rõ ràng
    # Thay vì r"√\1", ta dùng r"√(\1)"
    text = re.sub(r"√\s*[{<(]([^})>]+)[})>]", r"√(\1)", text)

    # Chuẩn hóa phân số
    text = re.sub(r"\\frac{([^}]+)}{([^}]+)}", r"(\1/\2)", text)
    # Chuẩn hóa vector
    text = re.sub(r"\\vec{([^}]+)}", r"\1⃗", text)
    # Chuẩn hóa góc dạng "hat"
    def add_hat(m):
        return m.group(1) + '\u0302'
    text = re.sub(r"\\hat{([A-Za-z])}", add_hat, text)
    # Chuẩn hóa chỉ số trên (superscript)
    def to_superscript(m):
        return m.group(1).translate(superscript_map)
    text = re.sub(r"\^\{([^}]+)\}", to_superscript, text)
    text = re.sub(r"\^([0-9n()+\-]+)", to_superscript, text)
    # Chuẩn hóa chỉ số dưới (subscript)
    def to_subscript(m):
        return m.group(1).translate(subscript_map)
    text = re.sub(r"_{([^}]+)}", to_subscript, text)
    text = re.sub(r"_([0-9aehijklmnoprstuvx]+)", to_subscript, text)
    # Chuẩn hóa công thức hóa học
    def chemical_subscripts(match):
        formula = match.group(0)
        return re.sub(r"(?<=[A-Za-z])([0-9]+)", lambda m: m.group(1).translate(subscript_map), formula)
    text = re.sub(r"\b([A-Z][a-z]?\d*)+", chemical_subscripts, text)

    # --- 4. Dọn dẹp cuối cùng ---
    text = text.replace("\\", "")
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------
# 🧩 API sinh đề trắc nghiệm (bản có TTL + force_regen)
# ---------------------------
@app.route("/api/generate-quiz", methods=["POST", "OPTIONS"])
def api_generate_quiz():
    start_time = time.time()
    try:
        # Try to parse JSON more robustly
        try:
            data = request.get_json(force=False, silent=True)
            if data is None:
                # Fallback: try reading raw data as text then json loads
                raw = request.data.decode("utf-8", errors="ignore")
                data = json.loads(raw) if raw else {}
        except Exception:
            data = {}
        # If still None -> empty dict
        data = data or {}

        # Log incoming payload (giúp debug)
        app.logger.info(f"Payload received: {data}")

        subject = data.get("subject", "")
        grade = str(data.get("grade", ""))
        topic = data.get("topic", "").strip()

        # Parse numbers an toàn (nếu frontend không gửi, dùng default)
        try:
            num_mcq = int(data.get("num_mcq", 10) or 10)
        except (ValueError, TypeError):
            num_mcq = 10
        try:
            num_tf = int(data.get("num_tf", 4) or 4)
        except (ValueError, TypeError):
            num_tf = 4

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
            app.logger.info("⚡ Trả đề từ cache RAM (hợp lệ trong TTL).")
            return jsonify(cached_entry["data"])

        # Nếu client gọi mà không có client AI config -> trả lỗi rõ
        if genai is None or not GOOGLE_API_KEY:
            app.logger.error("AI client not configured (genai or GOOGLE_API_KEY missing).")
            return jsonify({"error": "AI service not configured"}), 503

        # ---------------------------
        # PROMPT 1: MCQ
        # ---------------------------
        prompt_mcq = f"""
Chỉ trả về JSON hợp lệ, không markdown.
Tạo {num_mcq} câu hỏi trắc nghiệm nhiều lựa chọn (MCQ) cho học sinh:
- Môn học: {subject}
- Lớp: {grade}
- Chủ đề: {topic}
- Trong đó có 40% câu ở mức độ nhận biết, 30% câu ở mức độ hiểu, 30% câu ở mức độ vận dụng.
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
- Trong đó có 50% câu ở mức độ nhận biết, 25% câu ở mức độ hiểu, 25% câu ở mức độ vận dụng.
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
                if field in q and isinstance(q[field], str):
                    q[field] = normalize_math_symbols(q[field])
            if "options" in q and isinstance(q["options"], list):
                q["options"] = [normalize_math_symbols(opt) for opt in q["options"]]

        result = {"questions": all_questions[:expected_total]}

        # 💾 Lưu cache cùng timestamp
        quiz_cache[cache_key] = {"data": result, "time": time.time()}

        elapsed = round((time.time() - start_time) * 1000)
        app.logger.info(f"✅ Sinh đề hoàn tất: {len(result['questions'])} câu ({elapsed} ms)")
        return jsonify(result)

    except MethodNotAllowed:
        app.logger.warning("⚠️ Method not allowed on /api/generate-quiz")
        return jsonify({"error": "Method not allowed"}), 405

    except Exception as e:
        app.logger.error(f"❌ Exception: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "✅ AI_CHIRON26 backend is running"}), 200

# ------------------------------
# 🩺 HEALTH CHECK / KEEP ALIVE
# ------------------------------
@app.route("/ping", methods=["GET"])
def ping():
    """Route để kiểm tra backend còn sống hay không"""
    return {"status": "ok"}, 200

# ---------------------------
# 🚀 Run server
# ---------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
