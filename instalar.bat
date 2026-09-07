@echo off
REM MOD 24/7 — instalador de duplo-clique (Windows)
REM Se nada acontecer: instale o Python antes -> winget install Python.Python.3.12
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py instalar.py %*) else (python instalar.py %*)
pause
