@echo off
echo ------------------------------------------------------
echo Checando configuración para iniciar MVP1 de VALAC Joyas
echo ------------------------------------------------------

:: 1. Verificar que existe .git (repositorio local)
if not exist ".git" (
    echo [ERROR] No se encontró la carpeta .git. Asegurate de haber inicializado Git.
    echo Usa: git init
    goto :end
)

:: 2. Verificar que existe un remoto origin
set REMOTE_URL=
for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do (
    set REMOTE_URL=%%R
)

if "%REMOTE_URL%"=="" (
    echo [ERROR] No se encontró un remoto llamado origin. Configuralo usando:
    echo  git remote add origin https://github.com/GILVA20/valac_jewelry.git
    goto :end
)

:: 3. Verificar que existe la carpeta del entorno virtual venv
if not exist "venv\" (
    echo [ERROR] No se encontró la carpeta venv. Crea y/o activa el entorno virtual:
    echo  python -m venv venv
    echo  call venv\Scripts\activate
    goto :end
)

:: Si pasó todas las verificaciones:
echo [OK] Todas las verificaciones se han completado correctamente.
echo [OK] Repositorio local detectado, remoto configurado y entorno virtual listo.
echo [OK] Puedes empezar a agregar tu código para el MVP1 ahora. ¡Éxito!

:end
echo ------------------------------------------------------
