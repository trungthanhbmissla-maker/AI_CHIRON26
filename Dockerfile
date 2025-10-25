# ===============================
# 🐍 Sử dụng image Python nhẹ
# ===============================
FROM python:3.11-slim

# ===============================
# 📁 Thiết lập thư mục làm việc
# ===============================
WORKDIR /app

# ===============================
# 🧩 Copy mã nguồn vào container
# ===============================
COPY . /app

# ===============================
# ⚙️ Cài đặt dependencies
# ===============================
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r BACKEND_FLASK/requirements.txt || true
RUN pip install --no-cache-dir -r FRONTEND_STREAMLIT/requirements.txt || true

# ===============================
# 🌐 Mở cổng cho Render (Render gán PORT)
# ===============================
EXPOSE 5000
EXPOSE 8501

# ===============================
# 🏁 Chạy script khởi động cả Flask + Streamlit
# ===============================
CMD ["bash", "start.sh"]
