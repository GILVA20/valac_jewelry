# -*- coding: utf-8 -*-
"""
Admin: Productos (Supabase)

Este módulo define la vista de administración de productos con:
- Listado e índice enriquecido con galería
- Alta/edición/borrado
- Reordenamiento, borrado e imagen principal de la galería
- Subida segura a Supabase Storage desde backend
- Mejor UX en edición (mantenerse en la misma vista, portada automática)

Cambios clave (manteniendo funcionalidades):
- Rutas que reciben IDs como *string* (UUID) en lugar de <int:...>
- `set_primary` ya no depende de `product_id` en el form; lo obtiene de `product_images`
- `/update_gallery_order` acepta payload plano `[{id, orden}]` o `{"order":[...]}`
- Se elimina el casteo innecesario de IDs a `int` en queries
- Uso consistente de `self.app_sb` como cliente Supabase
- ✅ Reemplazo de `.select().single()` después de UPDATE/DELETE por `returning="representation"`
"""

from __future__ import annotations

# =========================
# Imports
# =========================
import os
import time
import uuid
import json
import logging
from typing import Any, Dict, List, Optional

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_admin import BaseView, expose  # type: ignore[attr-defined]
from flask_login import current_user

# Si tienes otras vistas admin en este paquete
from .admin_bulk_upload import BulkUploadAdminView  # noqa: F401  (referenciado por tu aplicación)

# Supabase client (v2)
try:
    from supabase import create_client as sb_create_client  # type: ignore
except Exception:  # pragma: no cover
    sb_create_client = None


# ============================================================
# Helpers
# ============================================================

def _get_cfg(key: str, default: Optional[str] = None) -> Optional[str]:
    """Obtiene config desde Flask config o ambiente."""
    return current_app.config.get(key) or os.environ.get(key) or default


def _coerce_float(value: Any) -> Optional[float]:
    """Convierte a float con seguridad."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _coerce_int(value: Any) -> Optional[int]:
    """Convierte a int con seguridad."""
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def _parse_json_list(raw: str) -> List[Any]:
    """Parsea un string JSON a lista. Devuelve [] si falla o no es list."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _success(msg: str) -> None:
    flash(msg, "success")


def _error(msg: str) -> None:
    flash(msg, "error")


def _info(msg: str) -> None:
    flash(msg, "info")


# ============================================================
# Vista Admin
# ============================================================

class SupabaseProductAdmin(BaseView):
    """
    Vista de administración de productos y su galería en Supabase.
    Requiere autenticación + rol admin.
    """

    # ---------------------------
    # Seguridad / acceso
    # ---------------------------
    def is_accessible(self) -> bool:
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        _error("Debes iniciar sesión como administrador para acceder a esta sección.")
        return redirect(url_for("auth.login", next=request.url))

    # ---------------------------
    # Supabase clients
    # ---------------------------
    def _get_service_supabase(self):
        """
        Devuelve un cliente Supabase usando SERVICE KEY si está disponible.
        Si no hay SERVICE KEY, cae en la anon key (no recomendado) y loguea warning.
        Se cachea en current_app para no recrearlo.
        """
        url = _get_cfg("SUPABASE_URL")
        service_key = _get_cfg("SUPABASE_SERVICE_KEY")
        anon_key = _get_cfg("SUPABASE_KEY")
        key = service_key or anon_key

        if not url or not key:
            raise RuntimeError("Config de Supabase incompleta (SUPABASE_URL / SUPABASE_KEY).")

        if not service_key:
            current_app.logger.warning(
                "[storage_upload] SUPABASE_SERVICE_KEY no configurado; usando anon key (no recomendado)."
            )

        if not hasattr(current_app, "_sb_service_client"):
            if sb_create_client is None:
                raise RuntimeError("supabase.create_client no disponible; instala supabase>=2.x")
            current_app._sb_service_client = sb_create_client(url, key)
        return getattr(current_app, "_sb_service_client")

    @property
    def app_sb(self):
        """Cliente Supabase 'application-level' ya creado por tu app (anon key)."""
        return self.admin.app.supabase

    # ---------------------------
    # Storage: subida segura
    # ---------------------------
    @expose("/storage/upload", methods=["POST"])
    def storage_upload(self):
        """
        Sube un archivo al bucket 'CatalogoJoyasValacJoyas' y devuelve su URL pública.
        Seguridad: usa SERVICE KEY en backend. No modifica tu esquema.
        Body: form-data con campo 'file'
        """

        def _extract_public_url(pub) -> Optional[str]:
            """Acepta str, dict u objeto y devuelve la URL pública."""
            if isinstance(pub, str):
                return pub
            if isinstance(pub, dict):
                return (
                    pub.get("publicUrl")
                    or pub.get("publicURL")
                    or (pub.get("data") or {}).get("publicUrl")
                    or (pub.get("data") or {}).get("publicURL")
                )
            # Objeto con atributos
            try:
                # attr directo
                direct = getattr(pub, "public_url", None) or getattr(pub, "publicURL", None)
                if direct:
                    return direct
                # objeto .data dict-like
                data = getattr(pub, "data", None)
                if isinstance(data, dict):
                    return data.get("publicUrl") or data.get("publicURL")
            except Exception:
                pass
            return None

        try:
            if "file" not in request.files:
                return jsonify({"error": "Archivo no recibido"}), 400

            f = request.files["file"]
            if not f or not f.filename:
                return jsonify({"error": "Nombre de archivo inválido"}), 400

            allowed = (".jpg", ".jpeg", ".png", ".webp")
            name_lower = f.filename.lower()
            if not any(name_lower.endswith(ext) for ext in allowed):
                return jsonify({"error": "Formato no permitido. Usa JPG/PNG/WEBP"}), 400

            # Genera una clave única
            import tempfile
            import shutil
            import mimetypes

            ext = os.path.splitext(name_lower)[1]
            key = f"products/{int(time.time() * 1000)}-{uuid.uuid4().hex}{ext}"

            mime = f.mimetype or mimetypes.guess_type(f.filename)[0] or "application/octet-stream"

            # Escribe a archivo temporal (storage3 abre el path con open())
            tmp = tempfile.NamedTemporaryFile(delete=False)
            try:
                f.stream.seek(0)
                shutil.copyfileobj(f.stream, tmp)
                tmp_path = tmp.name
            finally:
                try:
                    tmp.close()
                except Exception:
                    pass

            sb = self._get_service_supabase()

            # Subir pasando la ruta (string)
            # Algunas versiones aceptan dict de opciones con headers tipo S3
            sb.storage.from_("CatalogoJoyasValacJoyas").upload(
                key,
                tmp_path,
                {"content-type": mime, "x-upsert": "false"},
            )

            # Limpieza del tmp
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            # Obtener URL pública (manejar distintos retornos)
            pub = sb.storage.from_("CatalogoJoyasValacJoyas").get_public_url(key)
            public_url = _extract_public_url(pub)
            if not public_url:
                return jsonify({"error": "No se pudo obtener URL pública"}), 500

            # Cache bust
            return jsonify({"url": f"{public_url}?t={int(time.time() * 1000)}"}), 200

        except Exception as e:  # pragma: no cover
            current_app.logger.exception("[storage_upload] Error subiendo a Storage")
            return jsonify({"error": str(e)}), 500

    # ---------------------------
    # Índice
    # ---------------------------
    @expose("/", methods=["GET"])
    def index(self):
        sb = self.app_sb
        response = sb.table("products").select("*").execute()
        if not response.data:
            logging.error("Error al obtener productos: %s", response)
            products: List[Dict[str, Any]] = []
        else:
            products = response.data

            # Cargar todas las imágenes en un solo query y agrupar por product_id
            product_ids = [p["id"] for p in products]
            if product_ids:
                img_resp = (
                    sb.table("product_images")
                    .select("*")
                    .in_("product_id", product_ids)
                    .order("orden")
                    .execute()
                )

                images_by_product: Dict[str, List[Dict[str, Any]]] = {}
                for img in img_resp.data or []:
                    images_by_product.setdefault(img["product_id"], []).append(img)

                for prod in products:
                    prod["gallery"] = images_by_product.get(prod["id"], [])
            else:
                for prod in products:
                    prod["gallery"] = []

            logging.info("[index] Productos enriquecidos con galería: %d", len(products))

        return self.render("admin/supabase_products.html", products=products)

    # ---------------------------
    # Stock
    # ---------------------------
    @expose("/update-stock/<product_id>", methods=["POST"])
    def update_stock(self, product_id: str):
        sb = self.app_sb
        try:
            if "stock_total" not in request.form:
                _error("Falta el valor de stock_total en el formulario")
                return redirect(url_for("supabase_products.index"))

            new_stock = (request.form.get("stock_total") or "").strip()
            if not new_stock.isdigit() or int(new_stock) < 0:
                _error("El valor de stock debe ser un número entero positivo")
                return redirect(url_for("supabase_products.index"))

            new_stock_int = int(new_stock)

            response = (
                sb.table("products")
                .update({"stock_total": new_stock_int}, returning="representation")
                .eq("id", product_id)
                .execute()
            )

            if not response.data:
                current_app.logger.error(f"[update_stock] Error Supabase: {response}")
                _error("Ocurrió un error al actualizar el stock. Revisa los logs.")
            else:
                _success("Stock actualizado correctamente")

        except Exception:  # pragma: no cover
            current_app.logger.exception("[update_stock] Excepción inesperada")
            _error("Error inesperado al actualizar el stock")

        return redirect(url_for("supabase_products.index"))

    # ---------------------------
    # API: Edición rápida (AJAX/Inline)
    # ---------------------------
    @expose("/api/quick-update/<product_id>", methods=["PATCH"])
    def quick_update(self, product_id: str):
        """
        Endpoint para actualizaciones rápidas parciales vía AJAX.
        Valida campo, tipo y valor antes de actualizar en Supabase.

        Request:
            {
                "field": "precio|stock_total|descuento_pct",
                "value": <new_value>
            }

        Response (200 OK):
            {
                "status": "success",
                "updated_field": "precio",
                "new_value": 125.50,
                "precio_descuento": 112.50,
                "updated_at": "2025-01-21T14:30:00Z"
            }

        Response (400/422/500):
            {
                "status": "error",
                "message": "Descripción del error"
            }
        """
        sb = self.app_sb
        ALLOWED_FIELDS = {"precio", "stock_total", "descuento_pct", "nombre"}

        try:
            payload = request.get_json(force=True) if request.is_json else {}
            field = payload.get("field", "").strip()
            raw_value = payload.get("value")

            # ========== VALIDACIONES ==========
            # DEBUG: Log exact state
            current_app.logger.info(f"[DEBUG] ALLOWED_FIELDS = {ALLOWED_FIELDS}")
            current_app.logger.info(f"[DEBUG] field = '{field}' (type: {type(field).__name__})")
            current_app.logger.info(f"[DEBUG] field in ALLOWED_FIELDS = {field in ALLOWED_FIELDS}")

            # 1. Campo permitido
            if field not in ALLOWED_FIELDS:
                current_app.logger.warning(
                    "[quick_update] Campo no permitido: %s. Permitidos: %s", field, ALLOWED_FIELDS
                )
                return jsonify({
                    "status": "error",
                    "message": f"Campo '{field}' no permitido"
                }), 422

            # 2. Producto existe
            resp_check = sb.table("products").select("id, precio, stock_total").eq("id", product_id).execute()
            if not resp_check.data:
                current_app.logger.warning("[quick_update] Producto no encontrado: %s", product_id)
                return jsonify({
                    "status": "error",
                    "message": "Producto no encontrado"
                }), 404

            current_product = resp_check.data[0]
            current_price = float(current_product.get("precio") or 0)

            # ========== COERCIÓN Y VALIDACIÓN DE TIPOS ==========

            update_payload: Dict[str, Any] = {}
            new_value: Any = None

            if field == "precio":
                new_value = _coerce_float(raw_value)
                if new_value is None or new_value < 0:
                    return jsonify({
                        "status": "error",
                        "message": "Precio inválido: debe ser un número ≥ 0"
                    }), 400
                update_payload["precio"] = new_value
                # Recalcular precio_descuento si existe descuento
                resp_discount = sb.table("products").select("descuento_pct").eq("id", product_id).execute()
                discount_pct = 0
                if resp_discount.data:
                    discount_pct = int(resp_discount.data[0].get("descuento_pct") or 0)
                precio_descuento = round(new_value * (1 - discount_pct / 100.0), 2)
                update_payload["precio_descuento"] = precio_descuento

            elif field == "stock_total":
                new_value = _coerce_int(raw_value)
                if new_value is None or new_value < 0:
                    return jsonify({
                        "status": "error",
                        "message": "Stock inválido: debe ser un número entero ≥ 0"
                    }), 400
                update_payload["stock_total"] = new_value

            elif field == "descuento_pct":
                new_value = _coerce_int(raw_value)
                if new_value is None or not (0 <= new_value <= 100):
                    return jsonify({
                        "status": "error",
                        "message": "Descuento inválido: debe estar entre 0 y 100%"
                    }), 400
                update_payload["descuento_pct"] = new_value
                # Recalcular precio_descuento basado en precio actual
                precio_descuento = round(current_price * (1 - new_value / 100.0), 2)
                update_payload["precio_descuento"] = precio_descuento

            elif field == "nombre":
                new_value = str(raw_value).strip() if raw_value else None
                if not new_value or len(new_value) == 0:
                    return jsonify({
                        "status": "error",
                        "message": "Nombre inválido: no puede estar vacío"
                    }), 400
                if len(new_value) > 200:
                    return jsonify({
                        "status": "error",
                        "message": "Nombre inválido: máximo 200 caracteres"
                    }), 400
                update_payload["nombre"] = new_value

            # ========== ACTUALIZAR EN SUPABASE ==========

            upd_response = (
                sb.table("products")
                .update(update_payload, returning="representation")
                .eq("id", product_id)
                .execute()
            )

            if not upd_response.data:
                current_app.logger.error(
                    "[quick_update] Error Supabase UPDATE producto %s field %s: %s",
                    product_id, field, upd_response
                )
                return jsonify({
                    "status": "error",
                    "message": "Error al actualizar en la base de datos"
                }), 500

            updated_product = upd_response.data[0]
            response_field = field

            # Preparar respuesta con el precio_descuento actualizado
            response_data = {
                "status": "success",
                "updated_field": response_field,
                "new_value": new_value,
                "precio_descuento": float(updated_product.get("precio_descuento") or 0),
                "updated_at": updated_product.get("updated_at", ""),
            }

            current_app.logger.info(
                "[quick_update] Actualización exitosa: producto=%s field=%s new_value=%s",
                product_id, field, new_value
            )
            return jsonify(response_data), 200

        except Exception as e:  # pragma: no cover
            current_app.logger.exception("[quick_update] Excepción inesperada")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    # ---------------------------
    # Descuentos (bulk)
    # ---------------------------
    @expose("/apply_discount", methods=["POST"])
    def apply_discount(self):
        sb = self.app_sb
        ids = request.form.getlist("product_ids")
        pct = _coerce_int(request.form.get("bulk_descuento_pct", 0)) or 0

        for pid in ids:
            resp = sb.table("products").select("precio").eq("id", pid).execute()
            if resp.data:
                precio = float(resp.data[0]["precio"])
                precio_desc = round(precio * (1 - pct / 100.0), 2)
                sb.table("products").update(
                    {
                        "descuento_pct": pct,
                        "precio_descuento": precio_desc,
                    }
                ).eq("id", pid).execute()

        _success(f"Descuento {pct}% aplicado a {len(ids)} producto(s).")
        return redirect(url_for(".index"))

    @expose("/remove_discount", methods=["POST"])
    def remove_discount(self):
        sb = self.app_sb
        ids = request.form.getlist("product_ids")

        for pid in ids:
            sb.table("products").update(
                {
                    "descuento_pct": 0,
                    "precio_descuento": 0,
                }
            ).eq("id", pid).execute()

        _info(f"Descuentos eliminados de {len(ids)} producto(s).")
        return redirect(url_for(".index"))

    # ---------------------------
    # Alta
    # ---------------------------
    @expose("/new", methods=["GET", "POST"])
    def new(self):
        if request.method == "POST":
            nombre = request.form.get("nombre")
            descripcion = request.form.get("descripcion")
            precio_raw = request.form.get("precio")
            descuento_pct = _coerce_int(request.form.get("descuento_pct", 0)) or 0
            tipo_producto = request.form.get("tipo_producto")
            genero = request.form.get("genero")
            tipo_oro = request.form.get("tipo_oro")
            imagen_url = request.form.get("imagen")
            imagenes_raw = request.form.get("imagenes_multiples", "[]")

            if not all([nombre, descripcion, precio_raw, tipo_producto, genero, tipo_oro, imagen_url]):
                _error("Todos los campos son obligatorios.")
                return self.render("admin/supabase_new_product.html", config=current_app.config)

            precio = _coerce_float(precio_raw)
            if precio is None:
                _error("Precio inválido.")
                return self.render("admin/supabase_new_product.html", config=current_app.config)

            precio_descuento = round(precio * (1 - descuento_pct / 100.0), 2)

            sb = self.app_sb
            data = {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": precio,
                "descuento_pct": descuento_pct,
                "precio_descuento": precio_descuento,
                "tipo_producto": tipo_producto,
                "genero": genero,
                "tipo_oro": tipo_oro,
                "imagen": imagen_url,  # Primera imagen como principal
            }

            response = sb.table("products").insert(data).execute()

            if not response.data:
                _error("Error al agregar el producto: " + str(response))
                return redirect(url_for(".index"))

            nuevo_producto = response.data[0]
            producto_id = nuevo_producto["id"]

            # Imágenes múltiples
            imagenes = _parse_json_list(imagenes_raw)
            for i, url in enumerate(imagenes):
                try:
                    sb.table("product_images").insert(
                        {
                            "product_id": producto_id,
                            "imagen": url,
                            "orden": i,
                        }
                    ).execute()
                except Exception as ex:  # pragma: no cover
                    current_app.logger.exception(
                        "Excepción insertando imagen múltiple %s para producto %s: %s", url, producto_id, ex
                    )

            _success("Producto agregado exitosamente con imágenes.")
            return redirect(url_for(".index"))

        return self.render("admin/supabase_new_product.html", config=current_app.config)

    # ---------------------------
    # Borrado de producto
    # ---------------------------
    @expose("/delete/<product_id>", methods=["POST"])
    def delete_product(self, product_id: str):
        sb = self.app_sb
        try:
            # Eliminar dependencias antes del producto (silencioso si no existen)
            try:
                sb.table("product_views").delete().eq("product_id", product_id).execute()
            except Exception:
                pass
            sb.table("product_images").delete().eq("product_id", product_id).execute()

            # Producto
            response = sb.table("products").delete().eq("id", product_id).execute()

            if not response.data:
                _error("Error al eliminar el producto.")
            else:
                _success("Producto y registros relacionados eliminados exitosamente.")
        except Exception as e:  # pragma: no cover
            current_app.logger.exception("[delete_product] Error eliminando producto %s: %s", product_id, e)
            _error("Error al eliminar el producto. Revisa logs.")

        return redirect(url_for(".index"))

    # ---------------------------
    # Edición
    # ---------------------------
    @expose("/edit/<id>", methods=["GET", "POST"])
    def edit_product(self, id: str):
        sb = self.app_sb

        if request.method == "POST":
            current_app.logger.info("[edit_product] POST id=%s keys=%s", id, list(request.form.keys()))
            # --------- Campos del form ----------
            nombre = request.form.get("nombre")
            descripcion = request.form.get("descripcion")
            precio_raw = request.form.get("precio")
            descuento_pct_raw = request.form.get("descuento_pct", 0)
            tipo_producto = request.form.get("tipo_producto")
            genero = request.form.get("genero")
            tipo_oro = request.form.get("tipo_oro")
            imagen_url_form = request.form.get("imagen")
            nuevas_imagenes_raw = request.form.get("imagenes_multiples", "[]")

            # --------- Parseos y cálculos ----------
            nuevas_imagenes = _parse_json_list(nuevas_imagenes_raw)

            # Portada: si no viene del hidden pero hay nuevas, usar la primera nueva
            portada: Optional[str] = None
            if imagen_url_form and imagen_url_form != "undefined":
                portada = imagen_url_form
            elif nuevas_imagenes:
                portada = nuevas_imagenes[0]

            precio_float = _coerce_float(precio_raw)
            if precio_raw and precio_float is None:
                _error("Precio inválido.")
                # Si vino por fetch, responde JSON con error
                if request.headers.get("X-Requested-With") == "fetch":
                    return jsonify({"status": "error", "message": "Precio inválido"}), 400
                return redirect(url_for(".edit_product", id=id))

            d_pct = _coerce_int(descuento_pct_raw) or 0
            precio_descuento = (
                round(precio_float * (1 - d_pct / 100.0), 2) if (precio_float is not None) else 0.0
            )

            # --------- Payload limpio para UPDATE ----------
            update_data: Dict[str, Any] = {
                "nombre": (nombre or "").strip() or None,
                "descripcion": (descripcion or "").strip() or None,
                "precio": precio_float if precio_float is not None else None,
                "descuento_pct": d_pct,
                "precio_descuento": float(precio_descuento),
                "tipo_producto": (tipo_producto or "").strip() or None,
                "genero": (genero or "").strip() or None,
                "tipo_oro": (tipo_oro or "").strip() or None,
                "imagen": portada,  # puede quedar None si no cambia
            }
            clean_update_data = {k: v for k, v in update_data.items() if v is not None}
            current_app.logger.debug("[edit_product] UPDATE payload: %s", clean_update_data)

            # ✅ UPDATE con retorno de fila (compat supabase-py 2.x)
            upd = (
                sb.table("products")
                .update(clean_update_data, returning="representation")
                .eq("id", id)
                .execute()
            )

            if not upd.data:
                current_app.logger.error(f"[edit_product] Error UPDATE product {id}: {upd}")
                _error("Error al actualizar el producto.")
                if request.headers.get("X-Requested-With") == "fetch":
                    return jsonify({
                        "status": "error",
                        "message": "Error al actualizar el producto"
                    }), 400
                return redirect(url_for(".edit_product", id=id))

            # --------- Insertar nuevas imágenes en bulk ----------
            if nuevas_imagenes:
                current_max = 0
                try:
                    resp_ord = sb.table("product_images").select("orden").eq("product_id", id).execute()
                    if resp_ord.data:
                        current_max = max(img["orden"] for img in resp_ord.data)
                except Exception as e:
                    current_app.logger.warning("[edit_product] No se pudo leer orden actual: %s", e)

                payload_imgs = [
                    {"product_id": id, "imagen": url, "orden": current_max + i}
                    for i, url in enumerate(nuevas_imagenes, start=1)
                ]
                ins = sb.table("product_images").insert(payload_imgs).execute()
                if getattr(ins, "error", None):
                    current_app.logger.error(f"[edit_product] Error insertando nuevas imágenes: {ins.error}")
                    _error("El producto se actualizó, pero hubo errores agregando imágenes.")
                    if request.headers.get("X-Requested-With") == "fetch":
                        return jsonify({
                            "status": "error",
                            "message": "Producto actualizado, pero falló al agregar imágenes"
                        }), 400
                    return redirect(url_for(".edit_product", id=id))

            _success("Producto actualizado exitosamente.")
            # Si vino por fetch (AJAX), devuelve JSON; si no, redirige
            if request.headers.get("X-Requested-With") == "fetch":
                return jsonify({
                    "status": "ok",
                    "updated": True,
                    "added_images": len(nuevas_imagenes or []),
                    "redirect": url_for(".edit_product", id=id)
                }), 200

            return redirect(url_for(".edit_product", id=id))

        # --------- GET: traer datos actuales ----------
        resp = sb.table("products").select("*").eq("id", id).execute()
        if not resp.data:
            _error("Producto no encontrado.")
            return redirect(url_for(".index"))
        product = resp.data[0]

        try:
            images_response = (
                sb.table("product_images").select("*").eq("product_id", id).order("orden", desc=False).execute()
            )
            if images_response.data:
                gallery = images_response.data
                current_app.logger.info(
                    "[edit_product] Galería cargada: %d imágenes para producto %s", len(gallery), id
                )
            else:
                gallery = []
                current_app.logger.warning("[edit_product] Sin imágenes para producto %s", id)
        except Exception as e:  # pragma: no cover
            current_app.logger.exception("[edit_product] Error al cargar galería para producto %s: %s", id, e)
            gallery = []

        return self.render(
            "admin/supabase_edit_product.html",
            product=product,
            gallery=gallery,
            config=current_app.config,
        )

    # ---------------------------
    # Reordenar galería (AJAX)
    # ---------------------------
    @expose("/update_gallery_order", methods=["POST"])
    def update_gallery_order(self):
        sb = self.app_sb
        try:
            payload = request.get_json(force=True)
            # Acepta tanto lista plana como objeto con key "order"
            data = payload if isinstance(payload, list) else payload.get("order", [])

            if not isinstance(data, list):
                current_app.logger.error("[update_gallery_order] Formato inválido en payload: %s", payload)
                return jsonify({"status": "error", "message": "Formato inválido"}), 400

            current_app.logger.info("[update_gallery_order] Reordenando %d imágenes", len(data))

            for item in data:
                sb.table("product_images").update({"orden": int(item["orden"])}).eq("id", item["id"]).execute()

            return jsonify({"status": "success"}), 200
        except Exception as e:  # pragma: no cover
            current_app.logger.exception("[update_gallery_order] Error actualizando orden")
            return jsonify({"status": "error", "message": str(e)}), 500

    # ---------------------------
    # Borrar imagen de galería
    # ---------------------------
    @expose("/delete_gallery_image/<image_id>", methods=["POST"])
    def delete_gallery_image(self, image_id: str):
        sb = self.app_sb
        response = (
            sb.table("product_images")
            .delete(returning="representation")
            .eq("id", image_id)
            .execute()
        )
        if not response.data:
            _error("Error al eliminar la imagen de la galería.")
        else:
            _success("Imagen eliminada exitosamente.")
        return redirect(url_for(".edit_product", id=request.form.get("product_id")))

    # ---------------------------
    # Establecer principal (portada)
    # ---------------------------
    @expose("/set_primary/<image_id>", methods=["POST"])
    def set_primary(self, image_id: str):
        """
        Establece la imagen seleccionada como principal SIN modificar el esquema.
        Actualiza únicamente products.imagen = URL de la imagen elegida.
        """
        sb = self.app_sb

        # Obtener product_id y URL de la imagen desde product_images
        resp = sb.table("product_images").select("product_id, imagen").eq("id", image_id).single().execute()
        if not resp.data:
            _error("Imagen no encontrada.")
            return redirect(url_for(".index"))

        product_id = resp.data["product_id"]
        url = resp.data["imagen"]
        upd = (
            sb.table("products")
            .update({"imagen": url}, returning="representation")
            .eq("id", product_id)
            .execute()
        )
        if not upd.data:
            _error("No se pudo establecer la imagen principal.")
        else:
            _success("Imagen principal actualizada.")

        return redirect(url_for(".edit_product", id=product_id))

    # ---------------------------
    # Galería (vista simple)
    # ---------------------------
    @expose("/gallery")
    def gallery(self):
        sb = self.app_sb
        response = sb.table("products").select("id, nombre, imagen").execute()
        media_items = response.data or []
        return self.render("admin/supabase_gallery.html", media_items=media_items)


# ============================================================
# Otras vistas de ejemplo (como en tu app)
# ============================================================

class SalesAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        _error("Debes iniciar sesión como administrador para acceder a esta sección.")
        return redirect(url_for("auth.login", next=request.url))

    @expose("/")
    def index(self):
        sales: List[Dict[str, Any]] = []  # Simulación de datos de ventas
        logging.info("Ventas obtenidas: %s", sales)
        return self.render("admin/sales.html", sales=sales)


class PaymentsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        _error("Debes iniciar sesión como administrador para acceder a esta sección.")
        return redirect(url_for("auth.login", next=request.url))

    @expose("/", methods=["GET", "POST"])
    def index(self):
        if request.method == "POST":
            # Aquí procesarías el registro de un nuevo pago
            _success("Pago registrado exitosamente.")
            return redirect(url_for(".index"))
        payments: List[Dict[str, Any]] = []  # Simulación
        logging.info("Pagos obtenidos: %s", payments)
        return self.render("admin/payments.html", payments=payments)


class ReportsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        _error("Debes iniciar sesión como administrador para acceder a esta sección.")
        return redirect(url_for("auth.login", next=request.url))

    @expose("/")
    def index(self):
        report_data = {
            "total_sales": 100,
            "total_payments": 50,
            "inventory_count": 200,
        }
        logging.info("Reportes generados: %s", report_data)
        return self.render("admin/reports.html", report_data=report_data)
