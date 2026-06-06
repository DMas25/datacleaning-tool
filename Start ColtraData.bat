@echo off
title ColtraDataAi
cd /d "C:\Users\DAVIEMASWODZA\OneDrive - Coltrane Ltd\Desktop\DataCleaningApp"

echo Starting ColtraDataAi...
echo Browser will open at http://localhost:8502

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://localhost:8502'"

call ".venv\Scripts\activate.bat"
python -m streamlit run app.py --server.address localhost --server.port 8502 --server.headless true

pause
