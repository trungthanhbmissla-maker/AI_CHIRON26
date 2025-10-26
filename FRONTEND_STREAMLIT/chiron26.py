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
# 🏫 LOGO & TIÊU ĐỀ
# ================================
def load_logo_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

possible_paths = [
    Path(__file__).parent / "assets" / "logo.png",
    Path("assets/logo.png"),
    Path("logo.png"),
]
logo_b64 = next((load_logo_base64(p) for p in possible_paths if p.exists()), None)

if logo_b64:
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 10px;">
            <img src="data:image/png;base64,{logo_b64}" width="120">
        </div>
    """, unsafe_allow_html=True)

# ================================
# 💬 SIDEBAR
# ================================
with st.sidebar:
    st.image(str(Path("assets/logo.png")), width=80)
    st.markdown("## 🧭 Hướng dẫn sử dụng")
    st.markdown("""
    1. Chọn **môn học**, **lớp học** và **chủ đề**  
    2. Nhấn **🚀 Tạo đề trắc nghiệm**  
    3. Làm bài và **🛑 Nộp bài** khi hoàn thành  
    4. Xem **kết quả & đáp án chi tiết**
    """)
    st.markdown("---")
    st.info("**AI-Chiron26** hỗ trợ ôn tập trắc nghiệm bằng công nghệ AI & LLM.")

# ================================
# ⚙️ SESSION STATE
# ================================
defaults = {"quiz_data": None, "user_answers": {}, "start_time": None, "submitted": False, "end_time": None}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================================
# 📘 ĐỌC CHỦ ĐỀ
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "topics.json"))

if not os.path.exists(TOPICS_FILE):
    st.error(f"⚠️ Không tìm thấy tệp: {TOPICS_FILE}")
    st.stop()

with open(TOPICS_FILE, "r", encoding="utf-8") as f:
    topics_data = json.load(f)

subjects = list(topics_data.keys())
col1, col2 = st.columns(2)
subject = col1.selectbox("📘 Môn học", subjects)
grades = list(topics_data[subject].keys())
grade = col2.selectbox("🎓 Khối lớp", grades)
topic = st.selectbox("📖 Chủ đề", topics_data[subject][grade])

# ================================
# 🧠 GỌI BACKEND & LƯU SESSION
# ================================
if st.button("🚀 Tạo đề trắc nghiệm", type="primary"):
    with st.spinner("Đang tạo đề, vui lòng chờ..."):
        try:
            backend_url = os.getenv("BACKEND_URL", "https://ai-chiron26.onrender.com/api/generate-quiz")
            payload = {"subject": subject, "grade": grade, "topic": topic, "num_mcq": 10, "num_tf": 4}
            try:
                # 🧩 Kiểm tra backend có đang hoạt động không
                ping = requests.get("https://ai-chiron26.onrender.com", timeout=5)
                if ping.status_code != 200:
                    st.warning("⚠️ Backend đang khởi động, vui lòng thử lại sau vài giây.")
                    st.stop()
            except Exception:
                st.error("❌ Không thể kết nối tới backend. Thử lại sau 5s.")
                st.stop()

            # ✅ Nếu backend sẵn sàng thì mới gửi yêu cầu tạo đề
            try:
                res = requests.post(backend_url, json=payload, timeout=60)
                if res.status_code != 200:
                    st.error(f"❌ Backend trả về lỗi ({res.status_code}): {res.text}")
                    st.stop()
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Không thể gửi yêu cầu tới backend: {e}")
                st.stop()

            if res.status_code == 200:
                data = res.json()
                if "questions" in data:
                    st.session_state.quiz_data = data
                    st.session_state.user_answers = {}
                    st.session_state.submitted = False
                    st.session_state.start_time = time.time()
                    st.query_params["submitted"] = "0"
                    st.success(f"✅ Đã tạo {len(data['questions'])} câu hỏi!")
                else:
                    st.warning("⚠️ Không có câu hỏi hợp lệ từ backend.")
            else:
                st.error(f"❌ Lỗi backend ({res.status_code})")

        except Exception as e:
            st.error(f"❌ Lỗi kết nối backend: {e}")

# ================================
# 📋 HIỂN THỊ ĐỀ & CHẤM
# ================================
if st.session_state.quiz_data and "questions" in st.session_state.quiz_data:
    TIME_LIMIT = 15 * 60
    questions = st.session_state.quiz_data["questions"]

    st.header(f"📝 Đề trắc nghiệm môn {subject} - Lớp {grade}")
    st.caption(f"📖 Chủ đề: {topic}")
    st.markdown("---")

    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    end_time = int(st.session_state.start_time + TIME_LIMIT)
    remaining = max(0, int(end_time - time.time()))

    # ⏱ Hiển thị thời gian
    components.html(f"""
    <div id="timer" style="
        position: fixed; top: 20px; right: 25px;
        background: #e3f2fd; color: #0d47a1;
        padding: 10px 15px; border-radius: 8px;
        font-weight: bold; font-size: 18px;
        box-shadow: 0 0 6px rgba(0,0,0,0.2);
        z-index: 9999;">
        ⏱ {remaining//60:02d}:{remaining%60:02d}
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
        if (remaining <= 0) div.textContent = "⏱ Hết giờ!";
    }}
    setInterval(updateTimer, 1000);
    </script>
    """, height=60)

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.subheader(f"Câu {i+1}: {q.get('question', '')}")
                opts = q.get("options") or ["A", "B", "C", "D"]
                choice = st.radio("Chọn đáp án:", opts, key=f"q_{i}")
                st.session_state.user_answers[i] = choice
                st.markdown("---")

            if st.form_submit_button("🛑 Nộp bài"):
                st.session_state.submitted = True
                st.session_state.end_time = time.time()
                st.query_params["submitted"] = "1"
                st.rerun()

    else:
        score = sum(
            (st.session_state.user_answers.get(i, "")[:1].upper() ==
             (q.get("answer", "")[:1].upper()))
            for i, q in enumerate(questions)
        )
        st.success(f"🎯 Kết quả: {score}/{len(questions)} câu đúng ({score/len(questions)*100:.1f}%)")
        st.balloons()

        st.markdown("### 🔍 Đáp án chi tiết:")
        for i, q in enumerate(questions):
            st.markdown(f"**Câu {i+1}:** {q.get('question','')}")
            for opt in q.get("options", []):
                marker = "⬅️ (Bạn chọn)" if st.session_state.user_answers.get(i) == opt else ""
                st.write(f"- {opt} {marker}")
            st.info(f"✅ Đáp án đúng: {q.get('answer', '')}")
            st.markdown("---")
else:
    st.info("Chưa có đề — nhấn **🚀 Tạo đề trắc nghiệm** để bắt đầu.")
