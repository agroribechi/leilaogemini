@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "TESSERACT=C:\Program Files\Tesseract-OCR\tesseract.exe"
set "LEILAO_API_URL=http://127.0.0.1:8000"

if not exist "%PYTHON%" (
    echo Nao encontrei o ambiente Python do projeto.
    echo Execute primeiro as instrucoes do README.md.
    pause
    exit /b 1
)

if not exist "%TESSERACT%" (
    echo Nao encontrei o Tesseract em:
    echo %TESSERACT%
    pause
    exit /b 1
)

"%PYTHON%" -c "import PIL, mss, pytesseract" >nul 2>&1
if errorlevel 1 (
    echo Preparando os componentes necessarios. Isso pode levar alguns minutos somente na primeira vez...
    "%PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar os componentes. Verifique a conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
)

echo Iniciando Leilao OCR...
"%PYTHON%" app.py --tesseract "%TESSERACT%"

if errorlevel 1 (
    echo.
    echo O aplicativo foi encerrado por um erro. Copie esta mensagem e envie para o suporte.
    pause
)
