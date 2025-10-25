import base64
import os
import streamlit as st
import requests
import json
import time
import streamlit.components.v1 as components
from pathlib import Path

# ================================
# 🎨 CẤU HÌNH TRANG
# ================================
st.set_page_config(
    page_title="📚 Hệ thống ôn tập trắc nghiệm thông minh AI-Chiron26",
    layout="wide",
    page_icon="🎓"
)

# ================================
# 💎 CSS TUỲ BIẾN
# ================================
st.markdown("""
<style>
/* === Căn giữa logo trong sidebar === */
[data-testid="stSidebar"] img {
  display: block !important;
  margin-left: auto !important;
  margin-right: auto !important;
  margin-top: 18px !important;
  margin-bottom: 14px !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 14px rgba(0,0,0,0.18) !important;
  width: 96px !important; /* bạn có thể chỉnh kích thước nếu muốn */
}

/* Giữ lại màu nền mặc định, không dùng background ảnh */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: none !important;
  background-color: white !important;
}

/* Tiêu đề và nút giữ kiểu đẹp */
h1 {
  text-align: center;
  color: #0d47a1;
  font-weight: 800;
  margin-top: 0;
}
div.stButton > button {
  background-color: #0d47a1 !important;
  color: white !important;
  border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ================================
# 🏫 LOGO VÀ TIÊU ĐỀ
# ================================

def load_logo_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Thử tìm logo trong vài vị trí phổ biến
for path in ["logo.png", "assets/logo.png", "static/logo.png", "Backend_flask/assets/logo.png"]:
    logo_b64 = load_logo_base64(path)
    if logo_b64:
        break

if logo_b64:
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 10px;">
            <img src="data:image/png;base64,{logo_b64}" width="120">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("⚠️ Không tìm thấy logo.png, vui lòng đặt vào thư mục dự án hoặc 'assets/'.")
# ================================
# 🌟 HEADER ĐẸP + LOGO CĂN GIỮA
# ================================
st.markdown(
    """
    <style>
        .app-header {
            background: linear-gradient(135deg, #e3f2fd 0%, #fffde7 100%);
            border-radius: 16px;
            padding: 25px 15px 15px 15px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            animation: fadeIn 1.2s ease-in-out;
        }
        .app-header img {
            width: 110px;
            margin-bottom: 10px;
        }
        .app-header h1 {
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
            font-size: 32px;
            color: #1a237e;
            margin: 0;
        }
        .app-header p {
            font-size: 20px;
            color: #424242;
            margin-top: 5px;
            font-style: italic;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>

    <div class="app-header">
        <h1>📚 Hệ thống ôn tập trắc nghiệm thông minh AI – Chiron26</h1>
        <p>"Học thông minh, kiến tạo tương lai"</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ================================
# 💬 TIÊU ĐỀ
# ================================
#st.title("📚📚 Hệ thống ôn tập trắc nghiệm thông minh AI - Chiron26")

# ================================
# 💬 SIDEBAR - THÔNG TIN & HƯỚNG DẪN
# ================================

with st.sidebar:
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if not logo_path.exists():
        logo_path = Path("FRONTEND_STREAMLIT/assets/logo.png")

    if logo_path.exists():
        st.image(str(logo_path), width=80)
    else:
        st.warning("⚠️ Không tìm thấy logo.png, vui lòng đặt vào thư mục 'assets/'.")

    st.markdown("## 🧭 Hướng dẫn sử dụng")
    st.markdown("""
    1. Chọn **môn học**, **lớp học** và **chủ đề**.  
    2. Nhấn **🚀 Tạo đề trắc nghiệm** để hệ thống AI Chiron26 tạo tự động.  
    3. Làm bài và **🛑 Nộp bài** khi hoàn thành.  
    4. Xem **kết quả & đáp án chi tiết** ngay sau khi nộp.
    """)
    st.markdown("---")
    st.markdown("## 🤖 Thông tin hệ thống")
    st.info("""
    **AI-Chiron26** là hệ thống ôn tập trắc nghiệm thông minh. 
    Được phát triển dựa trên công nghệ **AI và LLM**.
    Hỗ trợ học sinh và giáo viên tạo, luyện tập và phân tích đề thi.  
    """)
    st.markdown("""
    📞 **Liên hệ hỗ trợ:**  
    Nguyễn Trung Thành  
    ✉️ [trungthanhbmissla@gmail.com](trungthanhbmissla@gmail.com)
    """)

# ================================
# ⚙️ KHỞI TẠO SESSION STATE
# ================================
defaults = {
    "quiz_data": None,
    "user_answers": {},
    "start_time": None,
    "submitted": False,
    "end_time": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================================
# 📘 ĐỌC FILE CHỦ ĐỀ
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "topics.json"))

if not os.path.exists(TOPICS_FILE):
    st.error(f"⚠️ Không thể tìm thấy tệp: {TOPICS_FILE}")
    st.stop()

with open(TOPICS_FILE, "r", encoding="utf-8") as f:
    topics_data = json.load(f)

if not topics_data or not isinstance(topics_data, dict):
    st.error("⚠️ Dữ liệu trong 'topics.json' không hợp lệ hoặc rỗng!")
    st.stop()

# ================================
# GIAO DIỆN NHẬP LIỆU
# ================================
subjects = list(topics_data.keys())
col1, col2 = st.columns(2)
subject = col1.selectbox("📘 Chọn môn học", subjects)

grades = list(topics_data[subject].keys())
grade = col2.selectbox("🎓 Chọn khối lớp", grades, index=min(len(grades)-1, 3))
topic = st.selectbox("📖 Chọn chủ đề", topics_data[subject][grade])

# ================================
# GỌI API TẠO ĐỀ
# ================================
if st.button("🚀 Tạo đề trắc nghiệm", type="primary"):
    with st.spinner("🧠 AI Chiron26 đang soạn đề, vui lòng chờ..."):
        try:
            api_url = "http://127.0.0.1:5000/api/generate-quiz"
            payload = {"subject": subject, "grade": grade, "topic": topic}
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                st.session_state.quiz_data = response.json()
                for k, v in defaults.items():
                    if k != "quiz_data":
                        st.session_state[k] = v
                st.success(f"✅ Tạo đề môn **{subject}** - Lớp **{grade}** - Chủ đề **{topic}** thành công!")
            else:
                st.error("❌ Lỗi từ backend: Không thể tạo đề.")
        except Exception as e:
            st.error(f"❌ Lỗi kết nối backend: {e}")

# ================================
# HIỂN THỊ ĐỀ & KẾT QUẢ
# ================================
if st.session_state.quiz_data and "questions" in st.session_state.quiz_data:
    TIME_LIMIT = 15 * 60
    questions = st.session_state.quiz_data["questions"]

    st.markdown("---")
    st.header(f"📝 Đề trắc nghiệm môn {subject} - Lớp {grade}")
    st.caption(f"📖 Chủ đề: {topic}")

    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    end_time = int(st.session_state.start_time + TIME_LIMIT)
    components.html(f"""
    <div id="timer" style="
        position: fixed;
        top: 20px;
        right: 25px;
        background: #e3f2fd;
        color: #0d47a1;
        padding: 10px 15px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0 0 6px rgba(0,0,0,0.2);
        z-index: 9999;">
        ⏱ 15:00
    </div>
    <script>
    const endTime = {end_time} * 1000;
    function updateTimer(){{
        const now = Date.now();
        const remaining = Math.max(0, Math.floor((endTime - now)/1000));
        const m = String(Math.floor(remaining/60)).padStart(2,'0');
        const s = String(remaining%60).padStart(2,'0');
        const div = document.getElementById("timer");
        if (div) div.textContent = `⏱ ${{m}}:${{s}}`;
        if (remaining<=0) window.location.search='?auto_submit=1';
    }}
    setInterval(updateTimer,1000);
    updateTimer();
    </script>
    """, height=60)

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.subheader(f"Câu {i+1}: {q['question']}")
                if q["type"] == "mcq":
                    st.session_state.user_answers[i] = st.radio(
                        "Chọn đáp án:", q["options"], index=None, key=f"q{i}"
                    )
                else:
                    st.session_state.user_answers[i] = st.radio(
                        "Chọn đáp án:", ["Đúng", "Sai"], index=None, key=f"q{i}"
                    )
                st.markdown("---")

            submit_btn = st.form_submit_button("🛑 Nộp bài")
            if submit_btn:
                st.session_state.submitted = True
                st.session_state.end_time = time.time()
                st.rerun()

    else:
        score = 0
        correct_answers = []

        for i, q in enumerate(questions):
            user_ans = st.session_state.user_answers.get(i)

            # ✅ Xác định đáp án đúng
            if q["type"] == "mcq":
                # Lấy option bắt đầu bằng ký tự đáp án (A/B/C/D)
                correct = next(
                    (opt for opt in q["options"] if opt.strip().startswith(q["answer"].strip())),
                    None
                )
            elif q["type"] in ["truefalse", "true_false"]:
                # Đáp án là "A" hoặc "B" => chuyển sang Đúng/Sai
                correct = "Đúng" if q["answer"].strip().upper() == "A" else "Sai"
            else:
                correct = None

            # ✅ So sánh kết quả
            if user_ans and correct and user_ans.strip() == correct.strip():
                score += 1

            correct_answers.append(correct)

        # ✅ Hiển thị kết quả tổng hợp
        total = len(questions)
        st.success(f"🎯 Kết quả: {score}/{total} câu đúng ({score/total*100:.1f}%)")
        st.balloons()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Xem lại đáp án"):
                with st.expander("📋 Chi tiết kết quả", expanded=True):
                    for i, q in enumerate(questions):
                        st.markdown(f"**Câu {i+1}:** {q['question']}")
                        st.info(f"✅ Đáp án đúng: {correct_answers[i]}")
                        st.write(f"👉 Bạn chọn: {st.session_state.user_answers.get(i) or 'Chưa chọn'}")
                        st.markdown("---")

        with col2:
            if st.button("🔁 Làm bài mới"):
                for k in defaults.keys():
                    st.session_state[k] = defaults[k]
                st.rerun()
