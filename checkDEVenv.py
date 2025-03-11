import os
import sys
import subprocess

# Variables de entorno esperadas
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_STORAGE_URL",
    "FLASK_ENV",
    "FLASK_APP"
]

# Archivos esenciales esperados
REQUIRED_FILES = [
    "valac_jewelry/app.py",
    "valac_jewelry/config.py",
    "requirements.txt",
    "Procfile",  # Necesario para Heroku
]

# Revisión de paquetes de producción
REQUIRED_PACKAGES = ["gunicorn", "flask", "supabase"]

def check_env_variables():
    """ Verifica que todas las variables de entorno necesarias estén configuradas """
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Faltan variables de entorno: {', '.join(missing_vars)}")
        print("❌  Asegúrate de definirlas en .env o en el entorno de ejecución.")
    else:
        print("✅  Todas las variables de entorno están correctamente configuradas.")

def check_flask_env():
    """ Verifica que Flask esté configurado correctamente según el entorno """
    flask_env = os.getenv("FLASK_ENV", "desarrollo")
    
    if flask_env.lower() == "production":
        print("✅  Flask está en modo PRODUCCIÓN.")
    elif flask_env.lower() == "development":
        print("⚠️  Flask está en modo DESARROLLO. 🚨 NO USAR EN PRODUCCIÓN.")
    else:
        print(f"⚠️  Flask tiene un valor de entorno desconocido: {flask_env}")

def check_supabase():
    """ Verifica si Supabase puede inicializarse correctamente """
    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌  Supabase URL o Key no están configuradas correctamente.")
            return
        
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.auth.get_user()
        
        if response:
            print("✅  Supabase está correctamente configurado y accesible.")
        else:
            print("❌  No se pudo autenticar en Supabase. Verifica las credenciales.")
    
    except ImportError:
        print("⚠️  No se encontró el paquete Supabase. Ejecuta 'pip install -r requirements.txt'.")
    except Exception as e:
        print(f"❌  Error conectando a Supabase: {e}")

def check_production_server():
    """ Revisa si Gunicorn o uWSGI están instalados para producción """
    try:
        result = subprocess.run(["gunicorn", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅  Gunicorn está instalado y disponible.")
        else:
            print("❌  Gunicorn no está instalado. Instálalo con 'pip install gunicorn'.")
    except FileNotFoundError:
        print("❌  Gunicorn no encontrado. Instalación recomendada: 'pip install gunicorn'.")

def check_required_files():
    """ Verifica que los archivos esenciales para el despliegue existan """
    missing_files = [f for f in REQUIRED_FILES if not os.path.exists(f)]
    
    if missing_files:
        print("❌  Faltan los siguientes archivos críticos:")
        for file in missing_files:
            print(f"   - {file}")
    else:
        print("✅  Todos los archivos esenciales existen.")

def check_required_packages():
    """ Verifica que los paquetes esenciales están instalados """
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌  Faltan los siguientes paquetes de producción: {', '.join(missing_packages)}")
        print("Ejecuta: pip install -r requirements.txt")
    else:
        print("✅  Todos los paquetes esenciales están instalados.")

if __name__ == "__main__":
    print("\n🔍 Iniciando verificación del entorno...\n")
    check_env_variables()
    check_flask_env()
    check_supabase()
    check_production_server()
    check_required_files()
    check_required_packages()
    print("\n✅  Verificación completada.")
