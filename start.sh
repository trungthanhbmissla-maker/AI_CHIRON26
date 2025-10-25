#!/bin/bash
# ==========================================
# 🚀 START SCRIPT FOR RENDER (AI_CHIRON26)
# ==========================================

# Chạy Flask backend ở nền
echo "🧠 Starting Flask backend..."
python BACKEND_FLASK/app.py &

# Đợi backend khởi động
sleep 5

# Chạy Streamlit frontend (Render tự gán PORT)
echo "🌐 Starting Streamlit frontend..."
streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=$PORT --server.address=0.0.0.0
