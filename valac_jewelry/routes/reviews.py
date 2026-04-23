"""
routes/reviews.py
Blueprint público de reseñas: API JSON + página /reseñas.
"""

import logging
import re
import uuid
from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

logger = logging.getLogger(__name__)

reviews_bp = Blueprint("reviews", __name__)

# ── Constantes ──────────────────────────────────────────────
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "mov"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov"}
MAX_PHOTO_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024   # 50 MB
MAX_FILES = 6
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
STORAGE_BUCKET = "CatalogoJoyasValacJoyas"
STORAGE_PREFIX = "products/reviews"


# ── Helpers ─────────────────────────────────────────────────

def _fecha_relativa(dt_str: str) -> str:
    """Convierte ISO timestamp a texto relativo en español."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Justo ahora"
        minutes = seconds // 60
        if minutes < 60:
            return f"Hace {minutes} min"
        hours = minutes // 60
        if hours < 24:
            return f"Hace {hours}h"
        days = diff.days
        if days == 1:
            return "Hace 1 día"
        if days < 30:
            return f"Hace {days} días"
        months = days // 30
        if months == 1:
            return "Hace 1 mes"
        if months < 12:
            return f"Hace {months} meses"
        return f"Hace más de un año"
    except Exception:
        return ""


def _abreviar_nombre(nombre: str) -> str:
    """'Ana García López' → 'Ana G.'"""
    parts = nombre.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return parts[0] if parts else "Cliente"


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _serialize_review(r: dict) -> dict:
    """Transforma row de Supabase a formato público JSON."""
    cdn = current_app.config.get("CDN_BASE_URL", "")
    media = r.get("media_urls") or []
    media_full = [f"{cdn}{u}" if not u.startswith("http") else u for u in media]
    return {
        "id": r["id"],
        "nombre": _abreviar_nombre(r.get("nombre", "")),
        "producto": r.get("producto", ""),
        "product_id": r.get("product_id"),
        "estrellas": r.get("estrellas", 5),
        "texto": r.get("texto", ""),
        "media_urls": media_full,
        "util_count": r.get("util_count", 0),
        "fecha_relativa": _fecha_relativa(r.get("created_at", "")),
        "verificado": r.get("verificado", False),
    }


def _get_client_ip() -> str:
    """IP real detrás de proxy."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


def _count_reviews_today(sb, ip: str) -> int:
    """Cuenta reseñas enviadas hoy desde esta IP."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
    try:
        resp = (
            sb.table("reviews")
            .select("id", count="exact")
            .eq("ip_address", ip)
            .gte("created_at", today)
            .execute()
        )
        return resp.count or 0
    except Exception:
        return 0


# ── GET /api/reviews/ ───────────────────────────────────────

@reviews_bp.route("/api/reviews/", methods=["GET"])
def list_reviews():
    """Lista reseñas verificadas con paginación y filtros."""
    sb = current_app.supabase

    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(18, max(1, request.args.get("per_page", 9, type=int)))
    product_id = request.args.get("product_id", type=int)
    estrellas = request.args.get("estrellas", type=int)
    con_media = request.args.get("con_media", "").lower() in ("1", "true")
    featured = request.args.get("featured", "").lower() in ("1", "true")

    offset = (page - 1) * per_page

    try:
        # Conteo total
        count_q = sb.table("reviews").select("id", count="exact").eq("verificado", "true")
        if product_id:
            count_q = count_q.eq("product_id", product_id)
        if estrellas and 1 <= estrellas <= 5:
            count_q = count_q.eq("estrellas", estrellas)
        count_resp = count_q.execute()
        total = count_resp.count or 0

        # Datos
        q = sb.table("reviews").select("*").eq("verificado", "true")
        if product_id:
            q = q.eq("product_id", product_id)
        if estrellas and 1 <= estrellas <= 5:
            q = q.eq("estrellas", estrellas)
        if con_media:
            # Filtrar las que tienen al menos un media_url
            q = q.neq("media_urls", "{}")

        if featured:
            q = q.order("estrellas", desc=True).order("created_at", desc=True).limit(6)
        else:
            q = q.order("created_at", desc=True).range(offset, offset + per_page - 1)

        resp = q.execute()
        reviews = [_serialize_review(r) for r in (resp.data or [])]

        return jsonify({
            "reviews": reviews,
            "total": total,
            "page": page,
            "has_more": (offset + per_page) < total,
        })
    except Exception as e:
        logger.exception("Error al listar reseñas: %s", e)
        return jsonify({"error": "Error al obtener reseñas"}), 500


# ── GET /api/reviews/stats ──────────────────────────────────

@reviews_bp.route("/api/reviews/stats", methods=["GET"])
def review_stats():
    """Estadísticas de reseñas: promedio, distribución por estrellas, total."""
    sb = current_app.supabase
    product_id = request.args.get("product_id", type=int)

    try:
        q = sb.table("reviews").select("estrellas").eq("verificado", "true")
        if product_id:
            q = q.eq("product_id", product_id)
        resp = q.execute()
        rows = resp.data or []

        total = len(rows)
        if total == 0:
            return jsonify({
                "total": 0,
                "promedio": 0,
                "distribucion": {str(i): 0 for i in range(1, 6)},
            })

        dist = {str(i): 0 for i in range(1, 6)}
        for r in rows:
            dist[str(r["estrellas"])] = dist.get(str(r["estrellas"]), 0) + 1

        promedio = sum(r["estrellas"] for r in rows) / total

        return jsonify({
            "total": total,
            "promedio": round(promedio, 1),
            "distribucion": dist,
        })
    except Exception as e:
        logger.exception("Error al obtener stats de reseñas: %s", e)
        return jsonify({"error": "Error al obtener estadísticas"}), 500


# ── POST /api/reviews/ ──────────────────────────────────────

@reviews_bp.route("/api/reviews/", methods=["POST"])
def create_review():
    """Recibe reseña con archivos media (multipart/form-data)."""
    sb = current_app.supabase

    # ── Rate limiting por IP (3 por día) ─────────────
    ip = _get_client_ip()
    if _count_reviews_today(sb, ip) >= 3:
        return jsonify({"error": "Has alcanzado el límite de reseñas por hoy. Intenta mañana."}), 429

    # ── Validar campos ───────────────────────────────
    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip()
    numero_pedido = (request.form.get("numero_pedido") or "").strip()
    producto = (request.form.get("producto") or "").strip()
    product_id = request.form.get("product_id", type=int)
    texto = (request.form.get("texto") or "").strip()

    try:
        estrellas = int(request.form.get("estrellas", 0))
    except (ValueError, TypeError):
        estrellas = 0

    errors = []
    if not nombre:
        errors.append("El nombre es requerido.")
    if not email or not EMAIL_RE.match(email):
        errors.append("Ingresa un email válido.")
    if not numero_pedido:
        errors.append("El número de pedido es requerido.")
    if not producto:
        errors.append("El nombre del producto es requerido.")
    if not (1 <= estrellas <= 5):
        errors.append("Selecciona entre 1 y 5 estrellas.")
    if len(texto) < 50:
        errors.append("Tu reseña debe tener al menos 50 caracteres.")

    if errors:
        return jsonify({"error": " ".join(errors)}), 400

    # ── Validar y subir archivos ─────────────────────
    files = request.files.getlist("media")
    if len(files) > MAX_FILES:
        return jsonify({"error": f"Máximo {MAX_FILES} archivos permitidos."}), 400

    media_paths: list[str] = []
    for f in files:
        if not f or not f.filename:
            continue
        ext = _ext(f.filename)
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"Formato .{ext} no permitido. Usa: jpg, png, webp, mp4, mov."}), 400

        # Leer contenido para verificar tamaño
        content = f.read()
        if ext in IMAGE_EXTENSIONS and len(content) > MAX_PHOTO_SIZE:
            return jsonify({"error": f"La imagen {f.filename} excede 10 MB."}), 400
        if ext in VIDEO_EXTENSIONS and len(content) > MAX_VIDEO_SIZE:
            return jsonify({"error": f"El video {f.filename} excede 50 MB."}), 400

        # Generar nombre seguro y subir
        safe_name = f"review_{uuid.uuid4().hex[:12]}_{uuid.uuid4().hex[:6]}.{ext}"
        storage_path = f"{STORAGE_PREFIX}/{safe_name}"  # products/reviews/xxx.jpg (bucket path)
        cdn_path = f"reviews/{safe_name}"  # reviews/xxx.jpg (CDN_BASE_URL ya incluye products/)

        mime_map = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
            "mp4": "video/mp4", "mov": "video/quicktime",
        }

        try:
            sb.storage.from_(STORAGE_BUCKET).upload(
                storage_path,
                content,
                {"content-type": mime_map.get(ext, "application/octet-stream")},
            )
            media_paths.append(cdn_path)
        except Exception as upload_err:
            logger.exception("Error subiendo archivo %s: %s", safe_name, upload_err)
            return jsonify({"error": "Error al subir archivos. Intenta de nuevo."}), 500

    # ── Insertar reseña en DB ────────────────────────
    review_data = {
        "nombre": nombre,
        "email": email,
        "numero_pedido": numero_pedido,
        "producto": producto,
        "product_id": product_id,
        "estrellas": estrellas,
        "texto": texto,
        "media_urls": media_paths,
        "verificado": False,
        "ip_address": ip,
    }

    try:
        sb.table("reviews").insert(review_data).execute()
        logger.info("Reseña creada exitosamente para producto=%s, ip=%s", producto, ip)
        return jsonify({
            "success": True,
            "message": "¡Gracias! Tu reseña ha sido enviada y está pendiente de aprobación.",
        }), 201
    except Exception as e:
        logger.exception("Error al insertar reseña: %s", e)
        return jsonify({"error": "Error al guardar la reseña. Intenta de nuevo."}), 500


# ── POST /api/reviews/<id>/util ─────────────────────────────

@reviews_bp.route("/api/reviews/<int:review_id>/util", methods=["POST"])
def vote_util(review_id: int):
    """Incrementa el contador de 'útil' de una reseña (1 voto por reseña por sesión)."""
    # Rate limit: 1 voto por reseña por sesión
    voted: list = session.get("reviews_voted", [])
    if review_id in voted:
        return jsonify({"error": "Ya votaste esta reseña."}), 429

    sb = current_app.supabase
    try:
        # Verificar que existe y está verificada
        resp = sb.table("reviews").select("util_count").eq("id", review_id).eq("verificado", "true").execute()
        if not resp.data:
            return jsonify({"error": "Reseña no encontrada."}), 404

        new_count = (resp.data[0].get("util_count") or 0) + 1
        sb.table("reviews").update({"util_count": new_count}).eq("id", review_id).execute()

        voted.append(review_id)
        session["reviews_voted"] = voted

        return jsonify({"util_count": new_count})
    except Exception as e:
        logger.exception("Error al votar útil: %s", e)
        return jsonify({"error": "Error al registrar voto."}), 500


# ── GET /resenas ─────────────────────────────────────────────

@reviews_bp.route("/resenas")
def resenas_page():
    """Página dedicada de reseñas (server-rendered, datos vía AJAX)."""
    return render_template("reviews.html")
