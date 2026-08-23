@echo off
setlocal EnableDelayedExpansion

echo ========================================================
echo         SISTEMA DE LEILAO EM TEMPO REAL - ARREMATE     
echo ========================================================
echo.

set "ROOT_DIR=%~dp0"
if exist "%ROOT_DIR%referenced-chatgpt-conversation-this-is-an" (
    set "BASE_DIR=%ROOT_DIR%referenced-chatgpt-conversation-this-is-an"
) else (
    set "BASE_DIR=%ROOT_DIR%"
)

set "PYTHON_API=%BASE_DIR%\leilao-api\.venv\Scripts\python.exe"
set "PYTHON_OCR=%BASE_DIR%\leilao-ocr-mvp\.venv\Scripts\python.exe"

if not exist "%PYTHON_API%" (
    echo [!] Ambiente virtual da API nao encontrado.
    echo Criando ambiente e instalando dependencias...
    py -m venv "%BASE_DIR%\leilao-api\.venv"
    "%BASE_DIR%\leilao-api\.venv\Scripts\pip.exe" install -r "%BASE_DIR%\leilao-api\requirements.txt"
)

echo [1/4] Iniciando API FastAPI (Porta 8000)...
start "Arremate - API Backend" /min cmd /c "cd /d "%BASE_DIR%\leilao-api" && "%PYTHON_API%" -m uvicorn app.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [2/4] Iniciando Painel Administrativo (Porta 5173)...
start "Arremate - Painel Admin" /min cmd /c "cd /d "%BASE_DIR%\painel-administrativo" && "%PYTHON_API%" -m http.server 5173"

echo [3/4] Iniciando App Mobile do Cliente (Porta 5174)...
start "Arremate - App Mobile" /min cmd /c "cd /d "%BASE_DIR%\app-cliente-mobile" && "%PYTHON_API%" -m http.server 5174"

echo [4/4] Abrindo interfaces no navegador...
timeout /t 1 /nobreak >nul
start http://127.0.0.1:5173
start http://127.0.0.1:5174

echo.
echo ========================================================
echo  [OK] SERVICOS INICIADOS COM SUCESSO!
echo ========================================================
echo  - API:                   http://127.0.0.1:8000/docs
echo  - Painel Administrativo: http://127.0.0.1:5173
echo  - App Cliente Mobile:    http://127.0.0.1:5174
echo ========================================================
echo.

set /p INICIAR_OCR="Deseja iniciar o Capturador Leilao OCR agora? (S/N): "
if /i "%INICIAR_OCR%"=="S" (
    echo.
    echo Iniciando Capturador OCR conectado a API...
    start "Arremate - Capturador OCR" cmd /c "cd /d "%BASE_DIR%\leilao-ocr-mvp" && set LEILAO_API_URL=http://127.0.0.1:8000 && "%PYTHON_OCR%" app.py --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe""
)

echo.
echo Para encerrar todos os servicos, execute Parar-Tudo.cmd ou feche as janelas.
echo.
pause
