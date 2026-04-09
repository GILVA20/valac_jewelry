from flask import request, redirect, url_for, flash, current_app, render_template
from flask_admin import BaseView, expose
from flask_login import current_user
import logging
import unicodedata
import csv
import io

try:
    import openpyxl
except ImportError:
    openpyxl = None

# ---------------------------------------------------------------------------
# Tablas de mapeo para formato Excel VALAC
# ---------------------------------------------------------------------------

# Normaliza un header: quita acentos, minúsculas, strip
def _norm(s: str) -> str:
    s = s.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

# Mapeo header normalizado → campo interno
_HEADER_MAP = {
    "fecha ingreso":       "fecha_ingreso",
    "id":                  "external_id",
    "nombre de pieza":     "nombre",
    "nombre":              "nombre",
    "linea":               "linea_raw",
    "t":                   None,           # columna tipo familia, ignorar
    "arete/brazalete/cadenas/pulsos": "tipo_producto_raw",
    "arete/brazalete/cu":  "tipo_producto_raw",
    "arete/brazalete":     "tipo_producto_raw",
    "tipo (arete/brazalete/collar)": "tipo_producto_raw",
    "tipo (arete/braz alete/collar)": "tipo_producto_raw",
    "tipo(arete/brazalete/collar)": "tipo_producto_raw",
    "tipo":                "tipo_producto_raw",
    "tipo producto":       "tipo_producto_raw",
    "tipo_producto":       "tipo_producto_raw",
    "peso (gramos)":       "peso_gramos",
    "peso(gramos)":        "peso_gramos",
    "peso":                "peso_gramos",
    "precio por gramo":    "precio_por_gramo",
    "precio/gramo":        "precio_por_gramo",
    "p":                   "precio_costo",
    "costo":               "precio_costo",
    "pf":                  "precio",
    "precio final":        "precio",
    "precio":              "precio",
    "estado":              "estado_inventario",
    "devolucion a":        "devolucion_a",
    "devolución a":        "devolucion_a",
    "genero":              "genero",
    "género":              "genero",
    "stock":               "stock_inicial",
    "stock inicial":       "stock_inicial",
    "imagen":              "imagen",
    "descripcion":         "descripcion",
    "descripción":         "descripcion",
}

# Linea → tipo_oro
_LINEA_ORO = {
    "f10":   "10k",
    "f10s":  "10k",
    "f14":   "14k",
    "f14s":  "14k",
    "f925":  "Plata .925",
    "f925s": "Plata .925",
    "fp":    "Plata .925",
    "fps":   "Plata .925",
    "925":   "Plata .925",
    "plata": "Plata .925",
}

# Tipo producto Excel → valor BD
_TIPO_PRODUCTO = {
    "arete":       "Aretes",
    "aretes":      "Aretes",
    "dije":        "Dijes",
    "dijes":       "Dijes",
    "cadena":      "Cadenas",
    "cadenas":     "Cadenas",
    "pulsera":     "Pulseras",
    "pulseras":    "Pulseras",
    "pulso":       "Pulsos",
    "pulsos":      "Pulsos",
    "anillo":      "Anillos",
    "anillos":     "Anillos",
    "gargantilla": "Collares",
    "collar":      "Collares",
    "collares":    "Collares",
}

# Estado inventario → valor BD
_ESTADO_INV = {
    "disponible":  "disponible",
    "vendido":     "vendido",
    "venta":       "vendido",
    "devolucion":  "devolucion",
    "devolucion":  "devolucion",
    "devolución":  "devolucion",
}

def _parse_float(val) -> float | None:
    if not val:
        return None
    cleaned = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _map_headers(fieldnames):
    """Devuelve dict {header_original: campo_interno} para los headers del CSV."""
    mapping = {}
    for h in (fieldnames or []):
        norm = _norm(h)
        # Primero busca coincidencia exacta
        if norm in _HEADER_MAP:
            mapping[h] = _HEADER_MAP[norm]
            continue
        # Busca si alguna clave conocida es prefijo/sufijo del header o viceversa
        matched = False
        for key, val in _HEADER_MAP.items():
            if val is None:
                continue
            # "tipo (arete/brazalete/collar)" contiene "arete/brazalete"
            if key in norm or norm in key:
                mapping[h] = val
                matched = True
                break
        if not matched:
            mapping[h] = None  # columna desconocida, ignorar
    return mapping


def _xlsx_to_csv_bytes(raw: bytes) -> bytes:
    """Convierte un archivo .xlsx a CSV (bytes) leyendo la primera hoja."""
    if openpyxl is None:
        raise RuntimeError("openpyxl no está instalado. pip install openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    output = io.StringIO()
    writer = csv.writer(output)
    for row in ws.iter_rows(values_only=True):
        # Convertir None a cadena vacía
        writer.writerow([(str(cell) if cell is not None else "") for cell in row])
    wb.close()
    return output.getvalue().encode("utf-8")


def process_csv(file):
    """
    Procesa CSV o XLSX exportado del Excel de inventario VALAC.
    Acepta tanto el formato Excel (Nombre de Pieza, Linea, Peso, etc.)
    como el formato legacy (nombre, precio, tipo_producto, ...).
    """
    valid_rows = []
    errors = []

    try:
        raw = file.read()

        # Detectar si es xlsx (ZIP magic bytes PK\x03\x04)
        if raw[:4] == b'PK\x03\x04':
            logging.info("Archivo detectado como XLSX, convirtiendo a CSV...")
            try:
                raw = _xlsx_to_csv_bytes(raw)
            except Exception as e:
                errors.append(f"Error al leer el archivo Excel: {e}")
                return {"valid_rows": valid_rows, "errors": errors}

        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            errors.append("No se pudo decodificar el archivo. Guarda el CSV como UTF-8.")
            return {"valid_rows": valid_rows, "errors": errors}

        # Normalizar line endings para que csv module lea correctamente
        # NO splitear por \n — csv.DictReader maneja campos quoted con newlines internos
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Detectar delimitador: Excel en español usa ; en vez de ,
        first_line = text.split('\n')[0] if text else ""
        if first_line.count(';') > first_line.count(','):
            delimiter = ';'
        else:
            delimiter = ','

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

        # Debug: log headers detectados y mapeo
        logging.info("CSV headers raw: %s", reader.fieldnames)
        logging.info("CSV delimiter: '%s'", delimiter)
        logging.info("CSV first line: %s", first_line[:200])
    except Exception as e:
        errors.append(f"Error al leer el CSV: {e}")
        return {"valid_rows": valid_rows, "errors": errors}

    if not reader.fieldnames:
        errors.append("El CSV está vacío o no tiene encabezados.")
        return {"valid_rows": valid_rows, "errors": errors}

    header_map = _map_headers(reader.fieldnames)
    logging.info("Header mapping: %s", header_map)
    fila_num = 1

    for raw_row in reader:
        fila_num += 1
        if len(valid_rows) >= 200:
            errors.append("Límite de 200 productos por carga alcanzado.")
            break

        # Normalizar valores — limpiar newlines internos de celdas multi-línea
        row = {}
        for k, v in raw_row.items():
            if isinstance(v, str):
                # "Pulso Rolex\nBi Color 21\ncm" → "Pulso Rolex Bi Color 21 cm"
                v = " ".join(v.split())
            row[k] = v

        # Traducir headers al campo interno
        r = {}
        for orig_h, campo in header_map.items():
            if campo and orig_h in row:
                r[campo] = row[orig_h]

        fila_errors = []

        # --- Nombre (obligatorio) ---
        nombre = r.get("nombre") or ""
        if not nombre:
            errors.append(f"Fila {fila_num}: Nombre vacío, fila omitida.")
            continue

        # --- tipo_oro: desde linea_raw o tipo_oro directo ---
        linea_raw = _norm(r.get("linea_raw") or r.get("tipo_oro", ""))
        tipo_oro = _LINEA_ORO.get(linea_raw)
        if not tipo_oro:
            errors.append(f"Fila {fila_num}: Línea/material '{r.get('linea_raw', '')}' no reconocido, fila omitida.")
            continue

        # --- tipo_producto ---
        tp_raw = _norm(r.get("tipo_producto_raw") or r.get("tipo_producto", ""))
        tipo_producto = _TIPO_PRODUCTO.get(tp_raw)
        if not tipo_producto:
            fila_errors.append(f"Fila {fila_num}: Tipo '{r.get('tipo_producto_raw', '')}' no reconocido, asignado 'Aretes'.")
            tipo_producto = "Aretes"

        # --- género ---
        genero_raw = (r.get("genero") or "").capitalize()
        genero = genero_raw if genero_raw in ("Mujer", "Hombre", "Unisex") else "Unisex"

        # --- peso y precio por gramo ---
        peso_gramos     = _parse_float(r.get("peso_gramos"))
        precio_por_gramo = _parse_float(r.get("precio_por_gramo"))

        # --- precio_costo: usar columna P si existe, sino calcular ---
        precio_costo_col = _parse_float(r.get("precio_costo"))
        if precio_costo_col:
            precio_costo = precio_costo_col
        elif peso_gramos and precio_por_gramo:
            precio_costo = round(peso_gramos * precio_por_gramo + 150, 2)
        else:
            precio_costo = None

        # --- precio (PF): usar columna PF si existe, sino precio_costo × 2 ---
        precio_col = _parse_float(r.get("precio"))
        if precio_col and precio_col >= 100:
            precio = precio_col
        elif precio_costo:
            precio = round(precio_costo * 2, 2)
        else:
            fila_errors.append(f"Fila {fila_num}: Sin precio ni datos para calcularlo, fila omitida.")
            errors.extend(fila_errors)
            continue

        if precio < 100:
            fila_errors.append(f"Fila {fila_num}: Precio ${precio} ajustado a $100.")
            precio = 100.0

        # --- estado inventario ---
        estado_raw = _norm(r.get("estado_inventario") or "disponible")
        estado_inventario = _ESTADO_INV.get(estado_raw, "disponible")

        # --- devolucion_a ---
        devolucion_a = (r.get("devolucion_a") or "").strip() or None

        # --- stock (joyas: default 1 pieza única) ---
        stock_raw = r.get("stock_inicial") or "1"
        try:
            stock = max(0, int(float(str(stock_raw).replace(",", ""))))
        except ValueError:
            stock = 1

        # --- external_id ---
        external_id = (r.get("external_id") or "").strip() or None

        # --- imagen ---
        imagen = (r.get("imagen") or "").strip() or None

        producto = {
            "nombre":           nombre,
            "descripcion":      r.get("descripcion") or "Sin descripción",
            "precio":           precio,
            "tipo_producto":    tipo_producto,
            "genero":           genero,
            "tipo_oro":         tipo_oro,
            "imagen":           imagen,
            "stock_inicial":    stock,
            "peso_gramos":      peso_gramos,
            "precio_por_gramo": precio_por_gramo,
            "precio_costo":     precio_costo,
            "estado_inventario": estado_inventario,
            "devolucion_a":     devolucion_a,
            "external_id":      external_id,
        }
        valid_rows.append(producto)
        errors.extend(fila_errors)

    summary = {"numero_productos_validos": len(valid_rows), "errores": errors}
    logging.info("Bulk upload: %d válidos, %d warnings.", len(valid_rows), len(errors))
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
            
            supabase = current_app.supabase
            inserted = 0
            insert_errors = []

            # Detectar columnas disponibles en la tabla
            _INVENTORY_COLS = {"peso_gramos", "precio_por_gramo", "precio_costo",
                               "estado_inventario", "devolucion_a"}
            try:
                probe = supabase.table("products").select("*").limit(1).execute()
                db_cols = set(probe.data[0].keys()) if probe.data else set()
                has_inventory = _INVENTORY_COLS.issubset(db_cols)
            except Exception:
                has_inventory = False

            if not has_inventory:
                current_app.logger.warning(
                    "Columnas de inventario no encontradas en BD. "
                    "Ejecuta migrations/002_inventory_tracking.sql en Supabase SQL Editor."
                )

            for product in valid_rows:
                row = {
                    "nombre":            product["nombre"],
                    "descripcion":       product["descripcion"],
                    "precio":            product["precio"],
                    "tipo_producto":     product["tipo_producto"],
                    "genero":            product["genero"],
                    "tipo_oro":          product["tipo_oro"],
                    "imagen":            product.get("imagen") or None,
                    "stock_total":       product.get("stock_inicial", 1),
                    "activo":            False,
                    "external_id":       product.get("external_id"),
                }
                if has_inventory:
                    row.update({
                        "peso_gramos":       product.get("peso_gramos"),
                        "precio_por_gramo":  product.get("precio_por_gramo"),
                        "precio_costo":      product.get("precio_costo"),
                        "estado_inventario": product.get("estado_inventario", "disponible"),
                        "devolucion_a":      product.get("devolucion_a"),
                    })
                # Quitar Nones para no pisar defaults de BD
                row = {k: v for k, v in row.items() if v is not None}
                resp = supabase.table("products").insert(row).execute()
                if resp.data:
                    inserted += 1
                else:
                    insert_errors.append(f"❌ No se insertó: {product['nombre']}")
                    current_app.logger.error(
                        "Error al insertar producto '%s': %s", product["nombre"], resp
                    )

            flash(f"Productos insertados en borrador: {inserted}", "success")
            for err in insert_errors:
                flash(err, "error")

            return redirect(url_for('.index'))
        
        return self.render("admin/bulk_upload.html")
