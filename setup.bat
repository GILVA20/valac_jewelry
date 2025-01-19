@echo off
echo Configurando el entorno de desarrollo para el proyecto VALAC Joyas...

:: Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv

:: Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate

:: Instalar dependencias
echo Instalando dependencias necesarias...
pip install --upgrade pip
pip install flask flask-sqlalchemy flask-wtf flask-bootstrap gunicorn firebase-admin

:: Instalar TailwindCSS
echo Instalando TailwindCSS...
npm install -g tailwindcss

:: Crear estructura de directorios
echo Creando estructura del proyecto...
mkdir valac_jewelry\static
mkdir valac_jewelry\templates
type nul > valac_jewelry\app.py
type nul > valac_jewelry\config.py
type nul > valac_jewelry\__init__.py

:: Crear archivo .gitignore
echo Creando archivo .gitignore...
(
    echo venv/
    echo __pycache__/
    echo *.sqlite3
    echo instance/
    echo *.log
    echo *.pyc
) > .gitignore

:: Inicializar repositorio Git
echo Inicializando repositorio Git...
git init
git remote add origin https://github.com/GILVA20/valac_jewelry.git

:: Hacer primer commit
git add .
git commit -m "Configuración inicial del proyecto VALAC Joyas"
git branch -M main
git push -u origin main

echo Entorno configurado correctamente. Para activar el entorno virtual, usa:
echo call venv\Scripts\activate
pause
