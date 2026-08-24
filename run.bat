@echo off
setlocal

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install --no-cache-dir -r requirements.txt

streamlit run app.py --server.port=8501
