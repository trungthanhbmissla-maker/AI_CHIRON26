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
# Khởi tạo các giá trị cần thiết nếu chúng chưa tồn tại
for key in ['quiz_data', 'user_answers', 'start_time', 'submitted']:
    if key not in st.session_state:
        st.session_state[key] = None

# ================================
# GIAO DIỆN NHẬP LIỆU
# ================================
subjects = ["Toán", "Vật lý", "Hóa học", "Sinh học", "Lịch sử", "Địa lý", "Tiếng Anh"]
grades = list(range(1, 13))

col1, col2 = st.columns(2)
with col1:
    subject = st.selectbox("Chọn môn học", subjects)
with col2:
    grade = st.selectbox("Chọn khối lớp", grades, index=9)

# ================================
# NÚT TẠO ĐỀ
# ================================
if st.button("🚀 Tạo đề trắc nghiệm", type="primary"):
    with st.spinner("🧠 AI đang soạn đề, vui lòng chờ..."):
        try:
            # ⚠️ THAY THẾ BẰNG URL BACKEND ONLINE CỦA BẠN KHI DEPLOY
            api_url = "http://127.0.0.1:5000/api/generate-quiz"
            payload = {"subject": subject, "grade": str(grade)}
            response = requests.post(api_url, json=payload)

            if response.status_code == 200:
                # Reset lại trạng thái cho bài thi mới
                st.session_state.quiz_data = response.json()
                st.session_state.user_answers = {}
                st.session_state.start_time = None
                st.session_state.submitted = False
                st.success("✅ Tạo đề thành công!")
                st.rerun() # Tải lại trang để bắt đầu làm bài
            else:
                st.error(f"❌ Lỗi từ backend: {response.json().get('error', 'Lỗi không xác định')}")
        except requests.exceptions.ConnectionError:
            st.error("❌ Không thể kết nối đến backend. Hãy kiểm tra server Flask.")
        except Exception as e:
            st.error(f"❌ Đã xảy ra lỗi: {e}")

# ================================
# HIỂN THỊ ĐỀ & XỬ LÝ LÀM BÀI
# ================================
if st.session_state.quiz_data and 'questions' in st.session_state.quiz_data:
    TIME_LIMIT = 15 * 60  # 15 phút
    questions = st.session_state.quiz_data['questions']

    # Bắt đầu tính giờ khi đề được hiển thị
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    st.markdown("---")
    st.header(f"📝 Đề kiểm tra môn {subject} - Lớp {grade}")

    # ================================
    # CHƯA NỘP BÀI -> HIỂN THỊ FORM LÀM BÀI
    # ================================
    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.subheader(f"Câu {i + 1}: {q['question']}")
                if q['type'] == 'mcq':
                    st.session_state.user_answers[i] = st.radio(
                        "Chọn đáp án:",
                        q['options'],
                        key=f"q_{i}",
                        index=None, # Không chọn sẵn đáp án nào
                        label_visibility="collapsed"
                    )
                elif q['type'] == 'true_false': # Sửa lại cho khớp JSON
                    st.session_state.user_answers[i] = st.radio(
                        "Chọn đáp án:",
                        ["Đúng", "Sai"],
                        key=f"q_{i}",
                        index=None,
                        label_visibility="collapsed"
                    )
                st.markdown("---")

            submitted = st.form_submit_button("🏁 Nộp bài")

            if submitted:
                st.session_state.submitted = True
                st.rerun() # Tải lại trang để hiển thị kết quả

    # ================================
    # ĐÃ NỘP BÀI -> HIỂN THỊ KẾT QUẢ
    # ================================
    else:
        # --- 1. Tính toán kết quả ---
        score = 0
        correct_answers_map = {}
        for i, q in enumerate(questions):
            user_answer = st.session_state.user_answers.get(i)
            correct_option_text = None
            if q['type'] == 'mcq':
                correct_option_text = next((opt for opt in q['options'] if opt.strip().startswith(q['answer'])), None)
            elif q['type'] == 'true_false':
                 correct_option_text = q['answer']

            if user_answer == correct_option_text:
                score += 1
            correct_answers_map[i] = correct_option_text

        total = len(questions)
        st.success(f"🎯 **Kết quả của bạn: {score}/{total} câu đúng ({score/total*100:.1f}%)**")
        if score == total:
            st.balloons()

        # --- 2. Hiển thị đáp án chi tiết ngay lập tức ---
        with st.expander("🧾 Xem lại đáp án chi tiết", expanded=True):
            for i, q in enumerate(questions):
                user_answer = st.session_state.user_answers.get(i)
                correct_answer = correct_answers_map.get(i)
                
                st.markdown(f"**Câu {i+1}:** {q['question']}")
                
                if user_answer == correct_answer:
                    st.write(f"✅ Bạn chọn: {user_answer} (Đúng)")
                else:
                    st.write(f"❌ Bạn chọn: {user_answer or 'Chưa chọn'}")
                    st.info(f"👉 Đáp án đúng: {correct_answer}")
                st.markdown("---")

        # --- 3. Nút làm lại bài ---
        if st.button("🔁 Làm lại bài mới", type="primary"):
            # Xóa toàn bộ trạng thái cũ để bắt đầu lại
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()