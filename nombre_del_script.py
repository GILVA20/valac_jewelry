import os

# Verificar la estructura de directorios
def check_directories(base_path):
    # Rutas a verificar
    required_dirs = [
        os.path.join(base_path, 'static', 'css'),
        os.path.join(base_path, 'static', 'images'),
        os.path.join(base_path, 'valac_jewelry', 'templates')
    ]
    
    # Verificar que las carpetas existen
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"Error: El directorio {dir_path} no existe.")
        else:
            print(f"Directorio {dir_path} encontrado.")
    
    # Archivos a verificar dentro de los directorios
    required_files = [
        os.path.join(base_path, 'static', 'css', 'output.css'),
        os.path.join(base_path, 'static', 'css', 'styles.css'),
        os.path.join(base_path, 'static', 'images', 'banner.jpg'),
        os.path.join(base_path, 'static', 'images', 'sapphire-ring.jpg'),
        os.path.join(base_path, 'static', 'images', 'diamond-earrings.jpg'),
        os.path.join(base_path, 'static', 'images', 'silver-bracelet.jpg'),
        os.path.join(base_path, 'valac_jewelry', 'templates', 'base.html'),
        os.path.join(base_path, 'valac_jewelry', 'templates', 'home.html')
    ]
    
    # Verificar existencia de archivos
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"Error: El archivo {file_path} no se encuentra.")
        else:
            print(f"Archivo {file_path} encontrado.")
    
# Definir el directorio base
base_path = 'C:/Repos/VALACJOYAS'

# Ejecutar la verificación
check_directories(base_path)
