# ===============================
# 🐍 Sử dụng Python 3.11 slim
# ===============================
FROM python:3.11-slim

WORKDIR /app

# Sao chép toàn bộ mã nguồn
COPY . /app

# Cài pip & các thư viện cần thiết
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r BACKEND_FLASK/requirements.txt || true
RUN pip install --no-cache-dir -r FRONTEND_STREAMLIT/requirements.txt || true

# Xóa cache để giảm dung lượng image
RUN rm -rf /root/.cache/pip

# Mở cổng (Render sẽ tự set $PORT)
EXPOSE 5000

# Chạy start.sh
CMD ["bash", "start.sh"]
