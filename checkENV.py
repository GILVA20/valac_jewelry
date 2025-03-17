import os
import sys
from pathlib import Path

# Colores para la salida en consola
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

# Función para verificar si un archivo existe
def check_file_exists(file_path, file_name):
    if not os.path.exists(file_path):
        print(f"{Colors.RED}✖ Error: El archivo {file_name} no existe en {file_path}{Colors.END}")
        return False
    print(f"{Colors.GREEN}✔ El archivo {file_name} existe.{Colors.END}")
    return True

# Función para verificar si una variable está definida en un archivo
def check_variable_in_file(file_path, variable_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if variable_name in content:
                print(f"{Colors.GREEN}✔ La variable {variable_name} está definida en {file_path}.{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}✖ Error: La variable {variable_name} NO está definida en {file_path}.{Colors.END}")
                return False
    except Exception as e:
        print(f"{Colors.RED}✖ Error al leer el archivo {file_path}: {e}{Colors.END}")
        return False

# Función para verificar importaciones en un archivo
def check_import_in_file(file_path, import_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            if f"from {import_name}" in content or f"import {import_name}" in content:
                print(f"{Colors.GREEN}✔ La importación {import_name} está presente en {file_path}.{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}✖ Error: La importación {import_name} NO está presente en {file_path}.{Colors.END}")
                return False
    except Exception as e:
        print(f"{Colors.RED}✖ Error al leer el archivo {file_path}: {e}{Colors.END}")
        return False

# Función principal
def main():
    print(f"{Colors.BLUE}=== Iniciando revisión del proyecto ==={Colors.END}")

    # Ruta base del proyecto
    base_path = Path("C:/Repos/VALACJOYAS")
    valac_jewelry_path = base_path / "valac_jewelry"

    # Verificar archivos
    files_to_check = [
        (base_path / ".env", "MP_ACCESS_TOKEN"),  # .env está en la raíz del proyecto
        (valac_jewelry_path / "config.py", "MP_ACCESS_TOKEN"),
        (valac_jewelry_path / "routes/mercadopago_checkout.py", "valac_jewelry.config"),
        (valac_jewelry_path / "app.py", "create_app"),
    ]

    for file_path, variable_or_import in files_to_check:
        print(f"\n{Colors.YELLOW}Revisando {file_path}:{Colors.END}")
        if check_file_exists(file_path, file_path.name):
            if file_path.name == ".env" or file_path.name == "config.py":
                check_variable_in_file(file_path, variable_or_import)
            else:
                check_import_in_file(file_path, variable_or_import)

    print(f"\n{Colors.BLUE}=== Revisión completada ==={Colors.END}")

if __name__ == "__main__":
    main()