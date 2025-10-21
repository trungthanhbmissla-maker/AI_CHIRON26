import streamlit as st
import requests
import time
import streamlit.components.v1 as components

# ================================
# CẤU HÌNH TRANG
# ================================
st.set_page_config(page_title="Tạo Đề Trắc Nghiệm AI", layout="centered")
st.title("📖 Tạo đề trắc nghiệm AI")

# ================================
# KHỞI TẠO SESSION STATE
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
# GIAO DIỆN NHẬP LIỆU
# ================================
subjects = ["Toán", "Vật lý", "Hóa học", "Sinh học", "Lịch sử", "Địa lý", "Tiếng Anh"]
grades = list(range(1, 13))

col1, col2 = st.columns(2)
subject = col1.selectbox("Chọn môn học", subjects)
grade = col2.selectbox("Chọn khối lớp", grades, index=9)

# ================================
# TẠO ĐỀ
# ================================
if st.button("🚀 Tạo đề trắc nghiệm", type="primary"):
    with st.spinner("🧠 AI đang soạn đề..."):
        try:
            api_url = "http://127.0.0.1:5000/api/generate-quiz"
            payload = {"subject": subject, "grade": str(grade)}
            response = requests.post(api_url, json=payload)

            if response.status_code == 200:
                st.session_state.quiz_data = response.json()
                st.session_state.user_answers = {}
                st.session_state.start_time = None
                st.session_state.submitted = False
                st.session_state.end_time = None
                st.success("✅ Tạo đề thành công!")
            else:
                st.error("❌ Lỗi từ backend.")
        except Exception as e:
            st.error(f"❌ Lỗi: {e}")

# ================================
# HIỂN THỊ ĐỀ
# ================================
if st.session_state.quiz_data and "questions" in st.session_state.quiz_data:
    TIME_LIMIT = 15 * 60
    questions = st.session_state.quiz_data["questions"]

    st.markdown("---")
    st.header(f"📝 Đề kiểm tra môn {subject} - Lớp {grade}")

    # Ghi lại thời điểm bắt đầu
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    # ================================
    # ĐỒNG HỒ CỐ ĐỊNH
    # ================================
    end_time = int(st.session_state.start_time + TIME_LIMIT)
    components.html(f"""
    <div id="timer" style="
        position: fixed;
        top: 20px;
        right: 25px;
        background: #fff3cd;
        color: #000;
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

    # ================================
    # FORM TRẢ LỜI
    # ================================
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

    # ================================
    # KẾT QUẢ
    # ================================
    else:
        score = 0
        correct_answers = []
        for i, q in enumerate(questions):
            user_ans = st.session_state.user_answers.get(i)
            correct = (
                q["answer"]
                if q["type"] == "true_false"
                else next((opt for opt in q["options"] if opt.startswith(q["answer"])), None)
            )
            if user_ans == correct:
                score += 1
            correct_answers.append(correct)

        total = len(questions)
        st.success(f"🎯 Kết quả: {score}/{total} câu đúng ({score/total*100:.1f}%)")
        st.balloons()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Kiểm tra kết quả"):
                with st.expander("📋 Xem lại đáp án", expanded=True):
                    for i, q in enumerate(questions):
                        st.markdown(f"**Câu {i+1}:** {q['question']}")
                        st.info(f"✅ Đáp án đúng: {correct_answers[i]}")
                        st.write(f"👉 Bạn chọn: {st.session_state.user_answers.get(i) or 'Chưa chọn'}")
                        st.markdown("---")
        with col2:
            if st.button("🔁 Làm lại bài mới"):
                for k in defaults.keys():
                    st.session_state[k] = defaults[k]
                st.rerun()
