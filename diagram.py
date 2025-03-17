import os

# Directorios y archivos a ignorar
ignore_dirs = ['node_modules', '__pycache__', '.git', 'venv']
ignore_files = ['package-lock.json', 'package.json', 'requirements.txt', 'setup.bat']

def save_code_structure(path, output_file, indent=0):
    """
    Recorre recursivamente el directorio 'path' y guarda en 'output_file'
    el nombre de cada archivo (con indentación según la profundidad) y su contenido.
    """
    # Obtener la lista de items ordenada para mantener consistencia
    for item in sorted(os.listdir(path)):
        # Ignorar directorios y archivos especificados
        if item in ignore_dirs or item in ignore_files:
            continue
        item_path = os.path.join(path, item)
        with open(output_file, "a", encoding="utf-8") as out:
            if os.path.isdir(item_path):
                # Escribir el nombre del directorio con indentación
                out.write("  " * indent + f"[{item}]\n")
                # Llamada recursiva para el subdirectorio (aumentando la indentación)
                save_code_structure(item_path, output_file, indent + 1)
            else:
                # Escribir el nombre del archivo
                out.write("  " * indent + f"{item}\n")
                # Separador
                out.write("  " * indent + "-" * 40 + "\n")
                try:
                    with open(item_path, "r", encoding="utf-8") as file:
                        content = file.read()
                    out.write(content + "\n")
                except Exception as e:
                    out.write(f"Error al leer el archivo: {e}\n")
                # Separador final para el archivo
                out.write("  " * indent + "=" * 40 + "\n\n")

def main():
    # Definir la ruta base del proyecto
    project_directory = "C:/Repos/VALACJOYAS"
    # Archivo de salida en el mismo directorio base (puedes ajustar la ruta si lo deseas)
    output_file = os.path.join(project_directory, "repo_code_structure.txt")
    
    # Si el archivo de salida ya existe, lo borramos para sobrescribirlo
    if os.path.exists(output_file):
        os.remove(output_file)
    
    # Llamar a la función para guardar la estructura y el contenido
    save_code_structure(project_directory, output_file)
    
    print(f"Código del repositorio guardado en: {output_file}")

if __name__ == "__main__":
    main()
