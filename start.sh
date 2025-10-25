#!/bin/bash
echo "🚀 Khởi động Flask backend..."
python BACKEND_FLASK/app.py &

echo "🌐 Khởi động Streamlit frontend..."
streamlit run FRONTEND_STREAMLIT/chiron26.py --server.port=$PORT --server.address=0.0.0.0
