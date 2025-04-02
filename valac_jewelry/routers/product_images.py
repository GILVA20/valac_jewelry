import io
import pandas as pd
import logging
from flask import Blueprint, request, jsonify, current_app

# Si handle_image está en este archivo, ya lo usamos.

bulk_upload_bp = Blueprint('bulk_upload_bp', __name__)

def handle_image(file):
    try:
        file.seek(0)
        content = file.read()  # content es de tipo bytes
        logging.debug("handle_image: Tamaño del archivo: %d bytes", len(content))
        logging.debug("handle_image: Nombre del archivo: %s", file.filename)
        if not content:
            logging.error("handle_image: El contenido del archivo está vacío.")
            return None

        # Verificar la imagen
        from PIL import Image
        from io import BytesIO
        image = Image.open(BytesIO(content))
        logging.debug("handle_image: Formato detectado: %s", image.format)
        image.verify()
        logging.debug("handle_image: Verificación de imagen exitosa")
    except Exception as e:
        logging.error("handle_image: Error al leer o verificar la imagen: %s", e)
        return None

    import os, hashlib
    md5_hash = hashlib.md5(content).hexdigest()
    ext = os.path.splitext(file.filename)[1] if hasattr(file, "filename") and file.filename else ".jpg"
    filename = f"{md5_hash}{ext}"
    # Usamos el bucket correcto (como en el flujo individual)
    bucket = "CatalogoJoyasValacJoyas/products"
    supabase = current_app.supabase

    try:
        files = supabase.storage.from_(bucket).list("")
        logging.debug("handle_image: Archivos existentes en bucket: %s", files)
        if any(f["name"] == filename for f in files):
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.debug("handle_image: La imagen ya existe. URL: %s", public_url)
            return public_url
    except Exception as e:
        logging.error("handle_image: Error al listar archivos en Supabase: %s", e)

    if len(content) > 2 * 1024 * 1024:
        try:
            image = Image.open(BytesIO(content))
            logging.debug("handle_image: Imagen para compresión, formato: %s", image.format)
            from io import BytesIO
            output = BytesIO()
            image.save(output, format=image.format, optimize=True, quality=70)
            content = output.getvalue()
            logging.debug("handle_image: Compresión exitosa, nuevo tamaño: %d bytes", len(content))
        except Exception as e:
            logging.error("handle_image: Error al comprimir la imagen: %s", e)

    try:
        upload_response = supabase.storage.from_(bucket).upload(filename, content)
        if upload_response:
            public_url = f"{current_app.config.get('SUPABASE_STORAGE_URL')}{filename}"
            logging.debug("handle_image: Imagen subida exitosamente. URL: %s", public_url)
            return public_url
        else:
            logging.error("handle_image: Fallo al subir la imagen a Supabase.")
            return None
    except Exception as e:
        logging.error("handle_image: Error al subir la imagen: %s", e)
        return None

@bulk_upload_bp.route("/bulk-upload", methods=["POST"])
def bulk_upload():
    if "csv" not in request.files:
        return jsonify({"error": "CSV no proporcionado"}), 400

    csv_file = request.files["csv"]
    # La opción 'image_paths' se podría usar para mapear archivos si se adjuntan, pero en este ejemplo lo usamos solo para referencia.
    image_paths = request.form.get("image_paths", "")
    image_paths_list = [p.strip() for p in image_paths.split(",") if p.strip()]

    try:
        content = csv_file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return jsonify({"error": "❌ Error: CSV no válido", "detail": str(e)}), 400

    required_columns = ["nombre", "descripcion", "precio", "tipo_producto", "genero", "tipo_oro", "imagen"]
    if not all(col in df.columns for col in required_columns):
        return jsonify({"error": "❌ Error: CSV no válido - columnas faltantes"}), 400

    total = len(df)
    report = {"success": [], "warnings": [], "errors": []}
    if total > 50:
        df = df.head(50)
        report["warnings"].append(f"⚠️ Solo se procesaron 50 de {total} productos.")

    supabase = current_app.supabase

    for _, row in df.iterrows():
        try:
            nombre = row.get("nombre", "Producto sin nombre")
            # Procesar la imagen:
            image_field = row.get("imagen", "")
            if isinstance(image_field, str) and image_field.startswith("http"):
                image_url = image_field
            else:
                # Se asume que image_field es una ruta local accesible en el servidor.
                try:
                    with open(image_field, "rb") as f:
                        # Para que handle_image funcione, agregamos un atributo filename si no existe.
                        if not hasattr(f, "filename"):
                            f.filename = os.path.basename(image_field)
                        image_url = handle_image(f)
                except Exception as e:
                    report["warnings"].append(f"❌ {nombre}: Error al subir imagen desde '{image_field}': {str(e)}")
                    continue

            if not image_url:
                report["warnings"].append(f"❌ {nombre}: No se obtuvo URL de imagen.")
                continue

            # Construir el objeto producto
            product_data = {
                "nombre": nombre,
                "descripcion": row.get("descripcion", ""),
                "precio": float(row.get("precio", 0)),
                "tipo_producto": row.get("tipo_producto", ""),
                "genero": row.get("genero", ""),
                "tipo_oro": row.get("tipo_oro", ""),
                "imagen": image_url
            }
            # Insertar el producto en Supabase
            response = supabase.table("products").insert(product_data).execute()
            if response.data:
                report["success"].append(f"{nombre}: Creado con ID {response.data[0]['id']}")
            else:
                report["warnings"].append(f"{nombre}: No se creó el producto (respuesta vacía)")
        except Exception as e:
            report["errors"].append(f"❌ {nombre}: {str(e)}")
    
    return jsonify(report)
