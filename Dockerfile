# ==========================
# 🐍 Dùng Python 3.10
# ==========================
FROM python:3.10

# ==========================
# 📂 Tạo thư mục làm việc
# ==========================
WORKDIR /app

# ==========================
# 📦 Copy toàn bộ mã nguồn vào container
# ==========================
COPY . /app

# ==========================
# 🧩 Cài thư viện cần thiết
# ==========================
RUN pip install --no-cache-dir flask flask-cors python-dotenv google-generativeai streamlit requests pandas

# ==========================
# 🌐 Cấu hình cổng (Render sẽ map tự động vào $PORT)
# ==========================
EXPOSE 10000

# ==========================
# 🚀 Chạy cả Flask và Streamlit song song
# ==========================
CMD bash -c "python BACKEND_FLASK/app.py & streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=\$PORT --server.address=0.0.0.0"
