#!/bin/bash
# Start FastAPI backend on port 8000 (internal)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit frontend on Render's assigned port
streamlit run frontend/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true

# Wait for both processes
wait
