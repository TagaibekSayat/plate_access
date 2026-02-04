@echo off
title PLATE ACCESS SYSTEM
echo Жүйе іске қосылуда...

:: 1. Виртуалды ортаны (venv) қосу
call venv\Scripts\activate

:: 2. Мәліметтер базасы мен AI-ды іске қосу
start "AI RECOGNITION" cmd /k python main.py

:: 3. Веб-интерфейсті (FastAPI) іске қосу
start "ADMIN PANEL" cmd /k uvicorn admin.app:app --host 0.0.0.0 --port 8000

echo ------------------------------------------
echo ✅ Бәрі дайын! 
echo 🌐 Админ панель: http://localhost:8000
echo ------------------------------------------
pause