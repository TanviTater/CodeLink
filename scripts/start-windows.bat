@echo off
echo Start backend in a separate terminal:
echo   cd backend ^&^& py -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt ^&^& uvicorn app.main:app --reload
echo.
echo Start frontend in another terminal:
echo   cd frontend ^&^& npm install ^&^& npm run dev
