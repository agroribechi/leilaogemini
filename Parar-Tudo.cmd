@echo off
setlocal

echo ========================================================
echo         ENCERRANDO TODOS OS SERVICOS DO ARREMATE
echo ========================================================
echo.

echo Finalizando processos nas portas 8000, 5173 e 5174...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5174" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [OK] Todos os servicos locais foram encerrados.
echo.
pause
