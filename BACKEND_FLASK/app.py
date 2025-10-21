import json 
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted


# 1️⃣ Tải biến môi trường
load_dotenv()

# 2️⃣ Khởi tạo Flask app
app = Flask(__name__)
CORS(app)

# 3️⃣ Lấy API key linh hoạt (ưu tiên .env, fallback nếu không có)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
    GOOGLE_API_KEY = "AIzaSyBo1nrSGr80CQgV9MDNoW4WVnKPesaZeAc"  # 🔧 Dán key dự phòng vào đây
    print("⚠️ Không tìm thấy GOOGLE_API_KEY trong .env → đang dùng key dự phòng trong code.")

if not GOOGLE_API_KEY:
    raise ValueError("❌ Không tìm thấy GOOGLE_API_KEY. Vui lòng đặt trong file .env hoặc trong code fallback.")

# 4️⃣ Cấu hình Gemini
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("✅ Cấu hình Gemini API thành công.")
except Exception as e:
    print(f"❌ Lỗi khi cấu hình Gemini API: {e}")
    raise

# 5️⃣ Danh sách model fallback
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-pro"
]

# 6️⃣ Hàm gọi Gemini an toàn, có fallback + xử lý finish_reason
def generate_text(prompt, safety_settings, generation_config):
    for model_name in MODELS_TO_TRY:
        try:
            print(f"🔄 Thử model: {model_name}")
            model = genai.GenerativeModel(model_name=model_name)
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )

            # ✅ Kiểm tra phản hồi hợp lệ
            if response and hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    parts = getattr(candidate.content, "parts", [])
                    text = ""
                    for p in parts:
                        if hasattr(p, "text"):
                            text += p.text
                    if text.strip():
                        print(f"✅ Thành công với model {model_name}")
                        return text.strip()

            print(f"⚠️ Model {model_name} không trả về nội dung hợp lệ (finish_reason={getattr(candidate, 'finish_reason', 'unknown')})")

        except ResourceExhausted:
            print(f"⚠️ Model {model_name} hết quota, thử model khác...")
            continue
        except Exception as e:
            print(f"❌ Lỗi với model {model_name}: {e}")
            continue

    raise Exception("Không có model nào phản hồi hợp lệ hoặc còn quota.")


@app.route('/')
def home():
    return jsonify({"message": "✅ Backend đang chạy!"})

# ======================
# API: Tạo đề trắc nghiệm
# ======================
@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json()
        subject = data.get("subject", "Toán")
        grade = data.get("grade", "10")

        prompt = f"""
        Chỉ trả về DUY NHẤT một đối tượng JSON hợp lệ, không có markdown, không có chú thích.
        Hãy tạo đề trắc nghiệm môn {subject} lớp {grade}, gồm:
        - 10 câu hỏi trắc nghiệm 4 lựa chọn (A, B, C, D)
        - 4 câu hỏi đúng/sai, mỗi câu có 2 lựa chọn ("Đúng", "Sai")

        Mẫu JSON chính xác như sau:
        {{
            "questions": [
                {{
                    "type": "mcq",
                    "question": "Câu hỏi 1...",
                    "options": ["A...", "B...", "C...", "D..."],
                    "answer": "B"
                }},
                {{
                    "type": "truefalse",
                    "question": "Câu hỏi đúng sai...",
                    "options": ["Đúng", "Sai"],
                    "answer": "Đúng"
                }}
            ]
        }}

        Các yêu cầu nghiêm ngặt:
        - Không dùng markdown (không ```json, không ```).
        - Không thêm mô tả, chỉ in ra JSON hợp lệ.
        - Câu hỏi và đáp án phải bằng tiếng Việt.
        - Đảm bảo JSON có thể phân tích trực tiếp bằng json.loads().
        """

        # Cấu hình AI
        safety_settings = {
            'HATE': 'BLOCK_NONE',
            'HARASSMENT': 'BLOCK_NONE',
            'SEXUAL': 'BLOCK_NONE',
            'DANGEROUS': 'BLOCK_NONE'
        }
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 8192
        }

        raw_text = generate_text(prompt, safety_settings, generation_config)

        print("\n--- Gemini Raw Response ---")
        print(raw_text)
        print("---------------------------\n")

        # --- Làm sạch chuỗi JSON ---
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        try:
            quiz_data = json.loads(raw_text)
            # Kiểm tra tối thiểu có trường "questions"
            if "questions" not in quiz_data:
                return jsonify({"error": "Dữ liệu AI trả về không có trường 'questions'."}), 500

            return jsonify(quiz_data)
        except json.JSONDecodeError:
            print("❌ LỖI: Dữ liệu AI không phải JSON hợp lệ.")
            return jsonify({"error": "AI trả về dữ liệu sai định dạng JSON."}), 500

    except Exception as e:
        print("❌ LỖI KHÁC:", e)
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
