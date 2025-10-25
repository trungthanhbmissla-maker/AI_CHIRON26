#!/bin/bash
# Khởi động Flask (chạy nền) + Streamlit (chạy chính)
python BACKEND_FLASK/app.py &
streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=$PORT --server.address=0.0.0.0
