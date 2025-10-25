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
[data-testid="stSidebar"] img {
  display: block !important;
  margin-left: auto !important;
  margin-right: auto !important;
  margin-top: 18px !important;
  margin-bottom: 14px !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 14px rgba(0,0,0,0.18) !important;
  width: 96px !important;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: none !important;
  background-color: white !important;
}
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
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

possible_paths = [
    Path(__file__).parent / "assets" / "logo.png",
    Path("FRONTEND_STREAMLIT/assets/logo.png"),
    Path("assets/logo.png"),
    Path("logo.png"),
]

logo_b64 = None
for path in possible_paths:
    if path.exists():
        logo_b64 = load_logo_base64(path)
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
    st.warning("⚠️ Không tìm thấy logo.png, vui lòng đặt vào thư mục 'assets/'.")

# ================================
# 🌟 HEADER
# ================================
st.markdown("""
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
""", unsafe_allow_html=True)

# ================================
# 💬 SIDEBAR
# ================================
with st.sidebar:
    st.image(str(Path("assets/logo.png")), width=80)
    st.markdown("## 🧭 Hướng dẫn sử dụng")
    st.markdown("""
    1. Chọn **môn học**, **lớp học** và **chủ đề**.  
    2. Nhấn **🚀 Tạo đề trắc nghiệm** để hệ thống AI Chiron26 tạo tự động.  
    3. Làm bài và **🛑 Nộp bài** khi hoàn thành.  
    4. Xem **kết quả & đáp án chi tiết** ngay sau khi nộp.
    """)
    st.markdown("---")
    st.info("""
    **AI-Chiron26** là hệ thống ôn tập trắc nghiệm thông minh 
    dựa trên công nghệ **AI và LLM** hỗ trợ học sinh và giáo viên.
    """)
    st.markdown("""
    📞 **Liên hệ:**  
    Nguyễn Trung Thành  
    ✉️ [trungthanhbmissla@gmail.com](trungthanhbmissla@gmail.com)
    """)

# ================================
# ⚙️ SESSION STATE
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
# 📘 ĐỌC CHỦ ĐỀ
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "topics.json"))

if not os.path.exists(TOPICS_FILE):
    st.error(f"⚠️ Không thể tìm thấy tệp: {TOPICS_FILE}")
    st.stop()

with open(TOPICS_FILE, "r", encoding="utf-8") as f:
    topics_data = json.load(f)

subjects = list(topics_data.keys())
col1, col2 = st.columns(2)
subject = col1.selectbox("📘 Chọn môn học", subjects)
grades = list(topics_data[subject].keys())
grade = col2.selectbox("🎓 Chọn khối lớp", grades)
topic = st.selectbox("📖 Chọn chủ đề", topics_data[subject][grade])

# ================================
# 🧠 GỌI API BACKEND (FIX 403 + AUTO DETECT)
# ================================
if st.button("🚀 Tạo đề trắc nghiệm", type="primary"):
    with st.spinner("🧠 AI Chiron26 đang soạn đề, vui lòng chờ..."):
        try:
            # Ưu tiên: đọc biến môi trường BACKEND_URL (trên Render)
            api_url = os.getenv("BACKEND_URL")

            # Nếu không có → dùng URL mặc định trên Render
            if not api_url:
                api_url = "https://ai-chiron26.onrender.com/api/generate-quiz"

            # 🔧 Gửi dữ liệu sang backend Flask
            payload = {
                "subject": subject,
                "grade": grade,
                "topic": topic,
                "num_mcq": num_mcq,
                "num_tf": num_tf,
                "force_regen": False
            }

            # 🧠 Gọi API
            res = requests.post(api_url, json=payload, timeout=60)

            if res.status_code == 200:
                data = res.json()
                if "questions" in data:
                    st.success(f"✅ Đã tạo {len(data['questions'])} câu hỏi!")
                    for i, q in enumerate(data["questions"], 1):
                        st.markdown(f"**Câu {i}:** {q['question']}")
                        for opt in q.get("options", []):
                            st.write(f"- {opt}")
                        st.write(f"**Đáp án:** {q['answer']}")
                else:
                    st.warning("⚠️ Không có dữ liệu hợp lệ từ backend.")
            else:
                st.error(f"❌ Lỗi backend ({res.status_code}): {res.text}")

        except Exception as e:
            st.error(f"❌ Lỗi kết nối backend: {e}")
            st.stop()

# ================================
# 📋 HIỂN THỊ ĐỀ & CHẤM
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
                st.session_state.user_answers[i] = st.radio(
                    "Chọn đáp án:",
                    q.get("options", ["A", "B", "C", "D"]),
                    index=None,
                    key=f"q{i}"
                )
                st.markdown("---")

            if st.form_submit_button("🛑 Nộp bài"):
                st.session_state.submitted = True
                st.session_state.end_time = time.time()
                st.rerun()

    else:
        score = 0
        for i, q in enumerate(questions):
            ans = st.session_state.user_answers.get(i)
            correct = q.get("answer", "").strip()
            if ans and correct and ans.strip().startswith(correct):
                score += 1
        total = len(questions)
        st.success(f"🎯 Kết quả: {score}/{total} câu đúng ({score/total*100:.1f}%)")
        st.balloons()
