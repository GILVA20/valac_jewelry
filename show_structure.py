import os

# Definir qué directorios y archivos ignorar
ignore_dirs = ['node_modules', '__pycache__', '.git', 'venv']
ignore_files = ['package-lock.json', 'package.json', 'requirements.txt', 'setup.bat']

def print_directory_structure(path, indent=0):
    """Función recursiva para imprimir la estructura de directorios, ignorando ciertos archivos y carpetas"""
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        # Ignorar archivos y carpetas no relevantes
        if item in ignore_dirs:
            continue
        if item in ignore_files:
            continue

        if os.path.isdir(item_path):
            print('  ' * indent + f'[{item}]')  # Muestra el nombre del directorio
            print_directory_structure(item_path, indent + 1)  # Llamada recursiva para subdirectorios
        else:
            print('  ' * indent + f'{item}')  # Muestra el nombre del archivo

# Ruta donde deseas comenzar a imprimir la estructura
project_directory = "C:/Repos/VALACJOYAS"  # Este es el nivel más alto de tu proyecto

print(f"Estructura de directorios de: {project_directory}")
print_directory_structure(project_directory)

