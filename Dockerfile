# ===============================
# 🐍 Sử dụng image Python ổn định và nhẹ
# ===============================
FROM python:3.11-slim

# ===============================
# 📁 Thiết lập thư mục làm việc
# ===============================
WORKDIR /app

# ===============================
# 🧩 Copy toàn bộ mã nguồn vào container
# ===============================
COPY . /app

# ===============================
# ⚙️ Cài đặt pip và dependencies
# ===============================
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r BACKEND_FLASK/requirements.txt || true
RUN pip install --no-cache-dir -r FRONTEND_STREAMLIT/requirements.txt || true

# ===============================
# 🌐 Expose cổng (Render tự gán)
# ===============================
EXPOSE 5000

# ===============================
# 🚀 Chạy cả backend & frontend
# ===============================
CMD ["bash", "start.sh"]
