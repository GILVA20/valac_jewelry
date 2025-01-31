import os
import shutil

def check_and_create_directories():
    # Rutas a las carpetas
    root_dir = os.path.abspath(os.getcwd())
    static_dir = os.path.join(root_dir, 'static')
    css_dir = os.path.join(static_dir, 'css')
    images_dir = os.path.join(static_dir, 'images')
    
    # Verifica si la carpeta "static/css" existe, si no la crea
    if not os.path.exists(css_dir):
        print(f"Creando la carpeta: {css_dir}")
        os.makedirs(css_dir)

    # Verifica si la carpeta "static/images" existe, si no la crea
    if not os.path.exists(images_dir):
        print(f"Creando la carpeta: {images_dir}")
        os.makedirs(images_dir)

def move_files():
    # Define las rutas para los archivos que se deben mover
    source_dir_valac_jewelry = os.path.join(os.getcwd(), 'valac_jewelry', 'static')
    target_dir = os.path.join(os.getcwd(), 'static', 'css')

    # Rutas de los archivos
    source_styles_css = os.path.join(source_dir_valac_jewelry, 'styles.css')
    source_output_css = os.path.join(source_dir_valac_jewelry, 'output.css')
    
    # Verifica si el archivo "styles.css" existe en la carpeta de valac_jewelry
    if os.path.exists(source_styles_css):
        target_styles_css = os.path.join(target_dir, 'styles.css')
        if os.path.exists(target_styles_css):
            print(f"El archivo {target_styles_css} ya existe, no se moverá.")
        else:
            print(f"Moviendo {source_styles_css} a {target_dir}")
            shutil.move(source_styles_css, target_dir)

    # Verifica si el archivo "output.css" existe en la carpeta de valac_jewelry
    if os.path.exists(source_output_css):
        target_output_css = os.path.join(target_dir, 'output.css')
        if os.path.exists(target_output_css):
            # Si el archivo ya existe, renombrarlo antes de mover
            new_target_output_css = os.path.join(target_dir, 'output_old.css')
            print(f"El archivo {target_output_css} ya existe, renombrándolo como {new_target_output_css}.")
            shutil.move(source_output_css, new_target_output_css)
        else:
            print(f"Moviendo {source_output_css} a {target_dir}")
            shutil.move(source_output_css, target_dir)

def verify_files():
    # Verifica si los archivos se movieron correctamente
    target_dir = os.path.join(os.getcwd(), 'static', 'css')
    
    # Archivos a verificar
    required_files = ['styles.css', 'output.css']
    
    for file in required_files:
        file_path = os.path.join(target_dir, file)
        if os.path.exists(file_path):
            print(f"[OK] El archivo {file} se encuentra en {file_path}.")
        else:
            print(f"[ERROR] El archivo {file} no se encuentra en {file_path}.")
        
def main():
    # Paso 1: Verificar y crear directorios si es necesario
    check_and_create_directories()
    
    # Paso 2: Mover los archivos necesarios
    move_files()
    
    # Paso 3: Verificar si los archivos están en el directorio correcto
    verify_files()

if __name__ == "__main__":
    main()
