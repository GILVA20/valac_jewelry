"""
Repo Splitter – versión ordenada con encabezados legibles
--------------------------------------------------------
Divide un repositorio en partes *.txt (≈230 KB cada una) y marca de forma clara
qué archivo pertenece a cada bloque. Además genera un árbol de la estructura.

• Mantiene el *orden alfabético* para que la lectura sea reproducible.
• Escribe encabezados y pies por cada archivo, ejemplo:

    ### BEGIN FILE: templates/home.html
    ...contenido...
    ### END FILE: templates/home.html

• Ignora carpetas/archivos configurados en IGNORE_DIRS / IGNORE_FILES.

Uso
---
python repo_splitter_ordered.py \
    --project-dir C:/Repos/VALACJOYAS \
    --output-dir C:/Repos/VALACJOYAS/repo_output_parts
"""

import argparse
import os
from pathlib import Path

IGNORE_DIRS = {"node_modules", "__pycache__", ".git", "venv"}
IGNORE_FILES = {
    "package-lock.json",
    "package.json",
    "requirements.txt",
    "setup.bat",
}

MAX_FILE_SIZE = 230_000  # ≈230 KB


def is_ignored(name: str) -> bool:
    """Determina si se ignora un archivo o directorio."""
    return name in IGNORE_DIRS or name in IGNORE_FILES


class PartWriter:
    """Gestiona la escritura segmentada en varios archivos de salida."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.part_index = 1
        self.current_size = 0
        self.current_file = None
        self.generated = []  # type: list[Path]
        self._open_new_file()

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    def _open_new_file(self):
        if self.current_file:
            self.current_file.close()
        filename = self.output_dir / f"repo_part_{self.part_index:02}.txt"
        self.current_file = filename.open("w", encoding="utf-8")
        self.generated.append(filename)
        self.current_size = 0
        self.part_index += 1

    def _ensure_capacity(self, size: int):
        if self.current_size + size > MAX_FILE_SIZE:
            self._open_new_file()

    # ------------------------------------------------------
    # Interface
    # ------------------------------------------------------
    def write_block(self, rel_path: str, content: str):
        """Escribe un bloque correspondiente a un archivo dado."""
        header = f"### BEGIN FILE: {rel_path}\n"
        footer = f"### END FILE: {rel_path}\n\n"
        block = header + content + ("\n" if not content.endswith("\n") else "") + footer
        encoded_len = len(block.encode("utf-8"))
        self._ensure_capacity(encoded_len)
        self.current_file.write(block)
        self.current_size += encoded_len

    def close(self):
        if self.current_file and not self.current_file.closed:
            self.current_file.close()


# ----------------------------------------------------------
# Recorre el árbol y escribe bloques
# ----------------------------------------------------------

def traverse_and_write(project_dir: Path, writer: PartWriter, tree_lines: list[str], rel_root: Path = Path("")):
    """Recorrido DFS en orden alfabético registrando estructura y contenidos."""
    entries = sorted(list(project_dir.iterdir()), key=lambda p: p.name.lower())
    for entry in entries:
        if is_ignored(entry.name):
            continue
        rel_path = rel_root / entry.name
        tree_lines.append("  " * len(rel_path.parents) + (f"[{entry.name}]" if entry.is_dir() else entry.name))

        if entry.is_dir():
            traverse_and_write(entry, writer, tree_lines, rel_path)
        else:
            try:
                content = entry.read_text(encoding="utf-8")
            except Exception as exc:
                content = f"<Error al leer archivo: {exc}>\n"
            writer.write_block(str(rel_path).replace(os.sep, "/"), content)


# ----------------------------------------------------------
# Script principal
# ----------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Divide repo en partes de texto legibles y ordenadas")
    parser.add_argument("--project-dir", required=True, help="Ruta del repo a dividir")
    parser.add_argument("--output-dir", required=True, help="Directorio de salida para los .txt generados")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Limpiar salidas previas
    for old in output_dir.glob("repo_part_*.txt"):
        old.unlink()
    tree_file_path = output_dir / "repo_structure_tree.txt"
    if tree_file_path.exists():
        tree_file_path.unlink()

    writer = PartWriter(output_dir)
    tree_lines: list[str] = []
    traverse_and_write(project_dir, writer, tree_lines)
    writer.close()

    # Guardar árbol de estructura
    tree_file_path.write_text("\n".join(tree_lines), encoding="utf-8")

    print("\n✅ División completada – Partes generadas:")
    for p in writer.generated:
        size_kb = p.stat().st_size / 1024
        print(f" - {p.name} ({size_kb:.1f} KB)")
    print(f"\n📁 Árbol de estructura: {tree_file_path}")


if __name__ == "__main__":
    main()
