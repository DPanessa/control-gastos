@echo off
cd /d "%~dp0"
echo Iniciando tu app de control de gastos...
python -m streamlit run app.py
pause