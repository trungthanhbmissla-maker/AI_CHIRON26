#!/bin/bash
# start.sh

# Chạy Flask backend ở nền
python BACKEND_FLASK/app.py &

# Chạy Streamlit frontend
streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=$PORT --server.address=0.0.0.0
