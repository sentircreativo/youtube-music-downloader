@echo off
title Descargador de Musica - Centro de Acompañamiento
echo Iniciando Descargador de Musica...
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un problema al iniciar la aplicacion. Presiona cualquier tecla para cerrar.
    pause
)
