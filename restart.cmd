@echo off
taskkill /F /IM python.exe
cd /d "c:\projetos\leilao chat\2026-08-19\referenced-chatgpt-conversation-this-is-an\leilao-api"
start "Arremate - API Backend" /min cmd /c ".\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
cd /d "c:\projetos\leilao chat\2026-08-19\referenced-chatgpt-conversation-this-is-an\painel-administrativo"
start "Arremate - Painel Admin" /min cmd /c "..\leilao-api\.venv\Scripts\python.exe -m http.server 5173"
cd /d "c:\projetos\leilao chat\2026-08-19\referenced-chatgpt-conversation-this-is-an\app-cliente-mobile"
start "Arremate - App Mobile" /min cmd /c "..\leilao-api\.venv\Scripts\python.exe -m http.server 5174"
