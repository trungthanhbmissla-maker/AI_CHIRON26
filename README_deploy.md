
# 🚀 Triển khai hệ thống AI_CHIRON26 lên Render

Hệ thống gồm **2 phần**:
- 🧠 **BACKEND_FLASK** — Xử lý API, sinh câu hỏi, lưu kết quả.
- 💻 **FRONTEND_STREAMLIT** — Giao diện người dùng cho học sinh & giáo viên.

---

## 🧩 1. Cấu trúc thư mục

AI_CHIRON26/
│
├── BACKEND_FLASK/
│ ├── app.py
│ ├── requirements.txt
│ ├── quiz_results.db
│ └── .env
│
├── FRONTEND_STREAMLIT/
│ ├── chiron26.py
│ ├── requirements.txt
│ └── assets/
│
├── Dockerfile
├── Procfile
├── start.sh
├── .gitignore
└── README_deploy.md

---

## ⚙️ 2. Nội dung các file quan trọng

### `.gitignore`
```bash
__pycache__/
*.pyc
*.pyo
venv/
*.env
*.db
.streamlit/
.vscode/


### Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r BACKEND_FLASK/requirements.txt || true
RUN pip install --no-cache-dir -r FRONTEND_STREAMLIT/requirements.txt || true
RUN rm -rf /root/.cache/pip

EXPOSE 5000
CMD ["bash", "start.sh"]

#Procfile
web: bash start.sh

##start.sh
#!/bin/bash
echo "🚀 Khởi động Flask backend..."
python BACKEND_FLASK/app.py &

echo "🌐 Khởi động Streamlit frontend..."
streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=$PORT --server.address=0.0.0.0

#Nhớ chạy lệnh sau trước khi commit:

chmod +x start.sh

🧠 3. Deploy lên Render

Push code lên GitHub

git add .
git commit -m "Deploy AI_CHIRON26"
git push origin main


Truy cập Render.com

→ Chọn New → Web Service
→ Kết nối repository AI_CHIRON26

Render sẽ tự phát hiện Dockerfile hoặc Procfile

Cấu hình:

Environment: Python 3

Region: Singapore (hoặc gần Việt Nam)

Build Command: (để trống nếu dùng Dockerfile)

Start Command: (Render tự nhận từ Procfile)

Nhấn “Deploy Web Service”

Render sẽ:

Tạo container

Cài đặt các thư viện

Chạy Flask backend và Streamlit frontend

Xuất ra URL công khai (ví dụ:
https://ai-chiron26.onrender.com)

🧩 4. Kiểm tra

Mở URL Render cung cấp

Giao diện Streamlit hiển thị: ✅

Gọi thử API /generate_quiz hoặc tương tự qua Postman: ✅

🧰 5. Một số lệnh hữu ích
# Chạy thử local
bash start.sh

# Cài requirements chung
pip install -r BACKEND_FLASK/requirements.txt
pip install -r FRONTEND_STREAMLIT/requirements.txt

# Cập nhật Docker image local
docker build -t ai_chiron26 .
docker run -p 5000:5000 ai_chiron26

🎯 Kết quả

Sau khi deploy thành công, bạn sẽ có:

Một ứng dụng web AI hoạt động 24/7

Streamlit UI + Flask API cùng hoạt động trong 1 container

Dễ dàng mở rộng, chỉnh sửa hoặc thêm tính năng AI sau này