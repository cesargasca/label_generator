@echo off
setlocal
rem Use UTF-8 in console (optional, for accents)
chcp 65001 >nul
set PYTHONUTF8=1

set "BASE=%~dp0"
set "PYDIR=%BASE%python-3.13.9-embed-amd64"
set "PYEXE=%PYDIR%\python.exe"

set "SCRIPT=%BASE%generate_labels.py"
set "INPUT=%BASE%invitados.txt"
set "OUTPUT=%BASE%etiquetas.pdf"

echo Generando PDF de etiquetas...
"%PYEXE%" "%SCRIPT%" "%INPUT%" "%OUTPUT%" --page letter --cols 3 --rows 10 --label-width-mm 51 --label-height-mm 25 --hspace-mm 3 --vspace-mm 3 --font-size 9

if errorlevel 1 (
  echo Ocurrio un error al generar el PDF.
  pause
  exit /b %errorlevel%
)

echo PDF generado correctamente: "%OUTPUT%"
start "" "%OUTPUT%"
pause
