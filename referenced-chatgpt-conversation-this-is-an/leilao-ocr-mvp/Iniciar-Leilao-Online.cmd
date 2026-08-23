@echo off
setlocal

rem Use este arquivo somente depois de iniciar a API local.
set "LEILAO_API_URL=http://127.0.0.1:8000"
call "%~dp0Iniciar-Leilao-OCR.cmd"
