import io
import os
import hashlib
import logging
import pandas as pd
from flask import Blueprint, request, jsonify, current_app
from PIL import Image
from io import BytesIO

bulk_upload_bp = Blueprint('bulk_upload_bp', __name__)

def handle_image(file, local_path=""):
    try:
        file.seek(0)
        content = file.read()  # contenido en bytes
        original_filename = file.filename
        logging.info("Procesando imagen: %s | Ruta local: %s", original_filename, local_path)
        if not content:
            logging.error("handle_image: El contenido del archivo está vacío.")
            return None, "error: contenido vacío", None
        # Verificar que el archivo es una imagen válida
        img = Image.open(BytesIO(content))
        logging.info("Imagen %s: Formato detectado: %s", original_filename, img.format)
        img.verify()
        logging.info("Imagen %s: Verificación exitosa", original_filename)
    except Exception as e:
        logging.error("handle_image: Error al leer/verificar %s: %s", original_filename, e)
        return None, f"error: verificación {e}", None

    # Validar que el archivo sea JPEG/JPG
    _, original_ext = os.path.splitext(original_filename) if original_filename else (".", ".jpg")
    original_ext = original_ext.lower()
    allowed_exts = [".jpg", ".jpeg"]
    if original_ext not in allowed_exts:
        logging.error("handle_image: Formato no permitido: %s. Solo se aceptan JPEG/JPG.", original_ext)
        return None, "error: formato no permitido", None

    # Calcular hash MD5 para fines de trazabilidad
    md5_hash = hashlib.md5(content).hexdigest()
    logging.info("Imagen %s: Hash MD5 calculado: %s", original_filename, md5_hash)
    # Usamos el nombre original (en minúsculas) para detectar duplicados
    filename = original_filename.lower()
    bucket = "CatalogoJoyasValacJoyas/products"
    supabase = current_app.supabase

    # Buscar duplicado: si ya existe, se reutiliza la URL.
    try:
        files = supabase.storage.from_(bucket).list("")
        logging.debug("handle_image: Archivos existentes en bucket:")
        for f in files:
            logging.debug(" - %s", f["name"])
        if any(f["name"] == filename for f in files):
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.info("Imagen %s: Duplicado detectado. Reutilizando URL.", original_filename)
            return public_url, "duplicado", md5_hash
    except Exception as e:
        logging.error("handle_image: Error al listar archivos: %s", e)

    # Compresión (opcional) si el archivo es mayor a 2MB
    if len(content) > 2 * 1024 * 1024:
        try:
            img = Image.open(BytesIO(content))
            output = BytesIO()
            img.save(output, format="JPEG", optimize=True, quality=70)
            content = output.getvalue()
            logging.info("Imagen %s: Compresión aplicada. Nuevo tamaño: %d bytes", original_filename, len(content))
        except Exception as e:
            logging.error("handle_image: Error al comprimir %s: %s", original_filename, e)

    try:
        upload_response = supabase.storage.from_(bucket).upload(filename, content)
        if upload_response:
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.info("Imagen %s: Subida exitosa. URL: %s", original_filename, public_url)
            return public_url, "subido", md5_hash
        else:
            logging.error("handle_image: Fallo al subir %s a Supabase.", original_filename)
            return None, "error: subida", md5_hash
    except Exception as e:
        logging.error("handle_image: Error al subir %s: %s", original_filename, e)
        return None, f"error: subida {e}", md5_hash

@bulk_upload_bp.route("/bulk-upload", methods=["POST"])
def bulk_upload():
    if "csv" not in request.files:
        return jsonify({"error": "CSV no proporcionado"}), 400

    csv_file = request.files["csv"]
    # Si se pasan rutas de imágenes adicionales en form-data (opcional)
    image_paths = request.form.get("image_paths", "")
    image_paths_list = [p.strip() for p in image_paths.split(",") if p.strip()]

    try:
        content = csv_file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        logging.info("CSV procesado correctamente. Registros: %d", len(df))
    except Exception as e:
        logging.error("bulk_upload: Error al procesar CSV: %s", e)
        return jsonify({"error": "❌ Error: CSV no válido", "detail": str(e)}), 400

    required_columns = ["nombre", "descripcion", "precio", "tipo_producto", "genero", "tipo_oro", "imagen"]
    if not all(col in df.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df.columns]
        logging.error("bulk_upload: Columnas faltantes en CSV: %s", missing_cols)
        return jsonify({"error": "❌ Error: CSV no válido - columnas faltantes", "missing_columns": missing_cols}), 400

    total = len(df)
    report = {"success": [], "warnings": [], "errors": []}
    preview_records = []  # Para CSV modificado
    log_records = []      # Para rastreo detallado

    if total > 50:
        df = df.head(50)
        report["warnings"].append(f"⚠️ Solo se procesaron 50 de {total} productos.")

    supabase = current_app.supabase

    for index, row in df.iterrows():
        nombre = row.get("nombre", "Producto sin nombre")
        descripcion = row.get("descripcion", "")
        precio = row.get("precio", 0)
        tipo_producto = row.get("tipo_producto", "")
        genero = row.get("genero", "")
        tipo_oro = row.get("tipo_oro", "")
        image_field = row.get("imagen", "")
        image_url = ""
        estado_imagen = ""
        hash_val = ""

        try:
            # Validar imagen: Si es URL, se utiliza directamente
            if isinstance(image_field, str) and image_field.lower().startswith("http"):
                image_url = image_field
                estado_imagen = "URL usada"
                hash_val = "N/A"
            else:
                # Intentar abrir archivo local
                try:
                    with open(image_field, "rb") as f:
                        if not hasattr(f, "filename"):
                            f.filename = os.path.basename(image_field)
                        image_url, estado_imagen, hash_val = handle_image(f, local_path=image_field)
                except Exception as e:
                    mensaje = f"❌ {nombre}: Error al procesar imagen desde '{image_field}': {str(e)}"
                    logging.warning(mensaje)
                    report["warnings"].append(mensaje)
                    estado_imagen = f"error: {e}"
                    image_url = ""
                    hash_val = ""
            log_records.append({
                "nombre": nombre,
                "ruta_local": image_field,
                "hash": hash_val if hash_val else "",
                "estado_imagen": estado_imagen
            })
            logging.info("Rastreo - Producto: %s | Ruta: %s | Hash: %s | Estado: %s",
                         nombre, image_field, hash_val, estado_imagen)

            # Creación o actualización del producto en Supabase
            product_data = {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": float(precio),
                "tipo_producto": tipo_producto,
                "genero": genero,
                "tipo_oro": tipo_oro,
                "imagen": image_url
            }

            # Utilizar upsert para crear o actualizar basado en 'nombre' como identificador único
            response = supabase.table("products").upsert(product_data, on_conflict=["nombre"]).execute()
            if response.data:
                product_id = response.data[0].get("id", "N/A")
                logging.info("Producto '%s' procesado correctamente. ID: %s", nombre, product_id)
                report["success"].append({"nombre": nombre, "id": product_id, "estado_imagen": estado_imagen})
            else:
                mensaje = f"❌ {nombre}: No se pudo insertar/actualizar el producto."
                logging.error("bulk_upload: %s", mensaje)
                report["errors"].append(mensaje)
                product_id = None

            # Agregar información al registro previo
            preview_record = row.to_dict()
            preview_record["image_url"] = image_url
            preview_record["product_id"] = product_id
            preview_records.append(preview_record)

        except Exception as e:
            mensaje = f"❌ {nombre}: {str(e)}"
            logging.error("bulk_upload: %s", mensaje)
            report["errors"].append(mensaje)

    # Generar CSV dinámico a partir de preview_records
    try:
        df_new = pd.DataFrame(preview_records)
        csv_buffer = io.StringIO()
        df_new.to_csv(csv_buffer, index=False)
        new_csv = csv_buffer.getvalue()
        report["csv_preview"] = new_csv
    except Exception as e:
        mensaje = f"Error al generar CSV dinámico: {str(e)}"
        logging.error("bulk_upload: %s", mensaje)
        report["warnings"].append(mensaje)

    report["log_rastreo"] = log_records

    return jsonify(report), 200
