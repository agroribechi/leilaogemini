@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Preparando ambiente da API...
    py -m venv .venv
)

"%PYTHON%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Instalando os componentes da API. Isso pode levar alguns minutos somente na primeira vez...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar os componentes. Verifique a conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
)

echo API iniciada em http://127.0.0.1:8000
echo Documentacao: http://127.0.0.1:8000/docs
echo Mantenha esta janela aberta durante o leilao.
"%PYTHON%" -m uvicorn --app-dir "%CD%" app.main:app --reload
pause
