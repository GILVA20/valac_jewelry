from flask import request, redirect, url_for, flash, current_app, render_template
from flask_admin import BaseView, expose
from flask_login import current_user
import logging
import csv
import io

def process_csv(file):
    """
    Procesa y valida un archivo CSV de productos.
    Retorna un diccionario con:
      - valid_rows: lista de diccionarios con productos válidos.
      - errors: lista de mensajes con errores y advertencias.
      - summary: resumen del proceso.
    """
    valid_rows = []
    errors = []
    required_columns = [
        "nombre", "descripcion", "precio", "tipo_producto", 
        "genero", "tipo_oro", "imagen", "stock_inicial"
    ]
    
    # Intentar leer el CSV con codificación UTF-8
    try:
        decoded_file = io.TextIOWrapper(file, encoding='utf-8')
        reader = csv.DictReader(decoded_file)
    except Exception as e:
        error_msg = f"Error al leer el archivo CSV: {e}"
        errors.append(error_msg)
        logging.error(error_msg)
        return {"valid_rows": valid_rows, "errors": errors}
    
    # Verificar que existan todas las columnas requeridas
    if not set(required_columns).issubset(reader.fieldnames):
        error_msg = f"El CSV no contiene las columnas requeridas. Se esperaban: {', '.join(required_columns)}"
        errors.append(error_msg)
        logging.error(error_msg)
        return {"valid_rows": valid_rows, "errors": errors}
    
    max_productos = 50
    producto_contador = 0
    fila_num = 1  # Cabezera considerada como fila 1
    
    for row in reader:
        fila_num += 1
        if producto_contador >= max_productos:
            break
        
        fila_errors = []
        # Quitar espacios en blanco de cada campo
        row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
        
        nombre = row.get("nombre")
        descripcion = row.get("descripcion") or "Sin descripción"
        precio_str = row.get("precio")
        tipo_producto = row.get("tipo_producto")
        genero = row.get("genero")
        tipo_oro = row.get("tipo_oro")
        imagen = row.get("imagen")
        stock_str = row.get("stock_inicial")
        
        # Conversión y validación numérica
        try:
            precio = float(precio_str)
        except Exception:
            fila_errors.append(f"Fila {fila_num}: Precio inválido '{precio_str}'.")
            precio = None
        
        try:
            stock = int(stock_str)
        except Exception:
            fila_errors.append(f"Fila {fila_num}: Stock inválido '{stock_str}'.")
            stock = None
        
        # Validar mínimo de precio (ajustar a 100 MXN)
        if precio is not None and precio < 100:
            logging.warning(f"Fila {fila_num}: Precio {precio} MXN menor a 100, ajustado a 100 MXN.")
            fila_errors.append(f"Fila {fila_num}: Precio ajustado a 100 MXN por ser menor al mínimo permitido.")
            precio = 100.0
        # Ajustar stock negativo
        if stock is not None and stock < 0:
            logging.warning(f"Fila {fila_num}: Stock negativo {stock}, ajustado a 0.")
            fila_errors.append(f"Fila {fila_num}: Stock negativo ajustado a 0.")
            stock = 0
        
        # Normalizar género (se espera "Mujer", "Hombre" o "Unisex")
        if genero:
            genero_normalizado = genero.capitalize()
            if genero_normalizado in ["Mujer", "Hombre", "Unisex"]:
                genero = genero_normalizado
            else:
                fila_errors.append(f"Fila {fila_num}: Género inválido '{genero}'.")
        else:
            fila_errors.append(f"Fila {fila_num}: Género es obligatorio.")
        
        # Validar tipo de oro: solo se aceptan "10k" o "14k"
        if tipo_oro not in ["10k", "14k"]:
            fila_errors.append(f"Fila {fila_num}: Tipo de oro inválido '{tipo_oro}', se omite producto.")
            errors.extend(fila_errors)
            continue  # Omite la fila de forma crítica
        
        # Validar tipo de producto (si no es reconocido, se asigna "Unisex")
        valid_tipos_producto = [
            "Anillos", "Collares", "Pulsos", "Cadenas",
            "Dijes Hombre", "Dijes Mujer", "Aretes", "Pulseras"
        ]
        if tipo_producto not in valid_tipos_producto:
            logging.warning(f"Fila {fila_num}: Tipo de producto '{tipo_producto}' no reconocido, se asigna 'Unisex'.")
            fila_errors.append(f"Fila {fila_num}: Tipo de producto no reconocido, se asignó 'Unisex'.")
            tipo_producto = "Unisex"
        
        # Alertas para stock
        if stock == 0:
            fila_errors.append(f"Fila {fila_num}: Stock es 0.")
        elif stock is not None and stock < 5:
            fila_errors.append(f"Fila {fila_num}: Bajo inventario: stock {stock}.")
        
        # Validar campos obligatorios
        if not nombre:
            fila_errors.append(f"Fila {fila_num}: Nombre es obligatorio.")
        if not imagen:
            fila_errors.append(f"Fila {fila_num}: Imagen es obligatoria.")
        
        producto = {
            "nombre": nombre,
            "descripcion": descripcion,
            "precio": precio,
            "tipo_producto": tipo_producto,
            "genero": genero,
            "tipo_oro": tipo_oro,
            "imagen": imagen,
            "stock_inicial": stock,
        }
        valid_rows.append(producto)
        producto_contador += 1
        errors.extend(fila_errors)
    
    summary = {
        "numero_productos_validos": len(valid_rows),
        "errores": errors
    }
    logging.info("Carga masiva procesada: %d productos válidos. Errores/advertencias: %s",
                 len(valid_rows), errors)
    return {"valid_rows": valid_rows, "errors": errors, "summary": summary}


class BulkUploadAdminView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))
    
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            file = request.files.get('csv_file')
            if not file:
                flash("No se ha seleccionado ningún archivo CSV.", "error")
                return self.render("admin/bulk_upload.html")
            
            result = process_csv(file)
            valid_rows = result.get("valid_rows", [])
            errors_list = result.get("errors", [])
            summary = result.get("summary", {})
            
            current_app.logger.info(f"Bulk upload procesado: {summary}")
            flash(f"Productos válidos: {summary.get('numero_productos_validos')}", "success")
            if errors_list:
                flash("Advertencias/Errores: " + "; ".join(errors_list), "warning")
            
            # Integración con Supabase:
            # Aquí podrías iterar sobre valid_rows e insertar cada producto.
            # Ejemplo:
            # supabase = current_app.supabase
            # for product in valid_rows:
            #     response = supabase.table("products").insert(product).execute()
            #     if not response.data:
            #         current_app.logger.error(f"Error al insertar producto: {product['nombre']} - {response}")
            
            # También se puede registrar el intento en un sistema de logs personalizado (e.g., inventory_logs)
            
            return redirect(url_for('.index'))
        
        return self.render("admin/bulk_upload.html")
