@echo off
setlocal

set "PYTHON=%~dp0..\leilao-api\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Nao encontrei o ambiente da API.
    echo Inicie a API uma vez pelo arquivo Iniciar-API.cmd e tente novamente.
    pause
    exit /b 1
)

echo Abrindo painel administrativo em http://127.0.0.1:5173
echo Mantenha esta janela aberta enquanto usa o painel.
start "" "http://127.0.0.1:5173"
"%PYTHON%" -m http.server 5173 --directory "%~dp0"
