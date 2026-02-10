@echo off
title PLATE ACCESS SYSTEM
echo Жүйе іске қосылуда...

:: 1. Виртуалды ортаны қосу
call venv\Scripts\activate

:: 2. AI + CAMERA (1 камера)
start "AI RECOGNITION" cmd /k python main.py --camera-index 0 --camera-type ENTRY --zone-id 1

:: 3. Веб-интерфейсті іске қосу
start "ADMIN PANEL" cmd /k uvicorn admin.app:app --host 0.0.0.0 --port 8000

echo ------------------------------------------
echo ✅ Бәрі дайын!
echo 🌐 Админ панель: http://localhost:8000
echo ------------------------------------------
pause
