@echo off
REM Este arquivo entra na pasta onde ele mesmo esta e roda o assistente.
REM Funciona mesmo se voce mover a pasta inteira para outro lugar.
cd /d "%~dp0"
python chat.py
pause
