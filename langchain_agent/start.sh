#!/bin/bash

# Start FastAPI backend in background
echo "Starting FastAPI backend..."
python api.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Streamlit frontend
echo "Starting Streamlit UI..."
streamlit run ui.py

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT
