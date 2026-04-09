# ========================================================================
#  Blueprint: /collection
#  Integra   :  • helper build_debug_sql()  ▶ muestra la sentencia lógica
#               • manejo correcto de APIResponse (supabase-py v2)
#               • logging INFO / ERROR coherente
# ========================================================================

from __future__ import annotations

from flask import Blueprint, render_template, request, current_app, flash
from textwrap import dedent
from typing import Any, Dict, List
import logging

collection_bp = Blueprint("collection", __name__, url_prefix="/collection")
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------- #
# Helper: genera la SQL que *conceptualmente* ejecuta supabase-py
# --------------------------------------------------------------------- #

def build_debug_sql(filters: Dict[str, Any], limit: int, offset: int) -> str:
    """Devuelve la sentencia SQL equivalente al query construido con
    supabase-py.  *Solo para depuración* (no se usa en producción)."""
    clauses: List[str] = []

    if (tp := filters.get("tipo_producto")):
        clauses.append(f"tipo_producto ILIKE '%{tp}%'")

    if (g := filters.get("genero")):
        if isinstance(g, list):
            valores = "', '".join(g)
            clauses.append(f"genero IN ('{valores}')")
        else:
            clauses.append(f"genero ILIKE '%{g}%'")

    if (to := filters.get("tipo_oro")):
        clauses.append(f"tipo_oro ILIKE '%{to}%'")

    if (p_min := filters.get("precio_min")) is not None:
        clauses.append(f"precio >= {p_min}")

    if (p_max := filters.get("precio_max")) is not None:
        clauses.append(f"precio <= {p_max}")

    where_sql = " AND ".join(clauses) or "TRUE"

    return dedent(f"""
        /* DEBUG-SQL · tabla products */
        SELECT *
        FROM products
        WHERE {where_sql}
        OFFSET {offset}
        LIMIT {limit};
    """).strip()


# --------------------------------------------------------------------- #
#  RUTA PRINCIPAL
# --------------------------------------------------------------------- #

@collection_bp.route("/", methods=["GET"])
def collection_home():
    """Renderiza la colección de productos con filtros, búsqueda y paginación."""

    supabase = current_app.supabase

    # ---------------------------- 1) Construcción del query dinámico -----
    #query = supabase.table("products").select("*")
    query = supabase.table("products").select(
        "id, nombre, descripcion, precio, descuento_pct, precio_descuento, " +
        "tipo_producto, genero, tipo_oro, imagen, created_at"
    ).eq("activo", True)
    logger.debug("📥 Query base creada")

    # Parámetros de la URL
    category   = request.args.get("category", "").strip()
    type_oro   = request.args.get("type_oro", "").strip()
    genero     = request.args.get("genero", "").strip().capitalize()
    mix_unisex = request.args.get("mix_unisex", "").strip()
    price_min  = request.args.get("price_min", "").strip()
    price_max  = request.args.get("price_max", "").strip()

    # Filtros ---------------------
    if category:
        query = query.ilike("tipo_producto", f"%{category}%")   # ← %…%
    if type_oro:
        query = query.ilike("tipo_oro",   f"%{type_oro}%") 

    genero_filter: Any = None
    if genero:
        if mix_unisex == "1" and genero in ("Hombre", "Mujer"):
            genero_filter = [genero, "Unisex"]
            query = query.in_("genero", genero_filter)
        else:
            genero_filter = genero
            query = query.eq("genero", genero)

    if price_min.isdigit():
        query = query.gte("precio", int(price_min))
    if price_max.isdigit():
        query = query.lte("precio", int(price_max))

    # Paginación ------------------
    page   = max(int(request.args.get("page", 1) or 1), 1)
    limit  = 36
    offset = (page - 1) * limit
    query  = query.range(offset, offset + limit - 1)

    # ---------------------------- 2) SQL conceptual para depuración -------
    filters = {
        "tipo_producto": category or None,
        "genero": genero_filter,
        "tipo_oro": type_oro or None,
        "precio_min": int(price_min) if price_min.isdigit() else None,
        "precio_max": int(price_max) if price_max.isdigit() else None,
    }
    logger.debug("\n%s", build_debug_sql(filters, limit, offset))

    # ---------------------------- 3) Ejecutar consulta en Supabase --------
    logger.info("🚀 Ejecutando consulta a Supabase …")
    try:
        response = query.execute()            # supabase-py v2
        products = response.data or []        # siempre obtenemos lista
        logger.info("📦 Filas recibidas = %s", len(products))
    except Exception as exc:
        logger.exception("❌ Supabase query falló: %s", exc)
        flash("Error al cargar los productos. Intenta de nuevo.", "error")
        return render_template("collection.html", products=[], page=page), 500

    # ---------------------------- 4) Búsqueda en memoria ------------------
    search = request.args.get("search", "").strip().lower()
    if search and products:
        antes = len(products)
        products = [
            p for p in products
            if search in (p.get("nombre", "") + " " + p.get("descripcion", "")).lower()
        ]
        logger.debug("🔍 Búsqueda='%s' filtró %s → %s", search, antes, len(products))

    # ---------------------------- 5) Ordenamiento -------------------------
    sort = request.args.get("sort", "")
    if sort == "precio_asc":
        products.sort(key=lambda x: x.get("precio", 0))
    elif sort == "precio_desc":
        products.sort(key=lambda x: x.get("precio", 0), reverse=True)
    elif sort == "novedades":
        products.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort == "mas_vendidos":
        products.sort(key=lambda x: x.get("ventas", 0), reverse=True)
    elif sort == "destacados":
        products.sort(key=lambda x: x.get("destacado", False), reverse=True)
    elif sort == "mejor_valoracion":
        products.sort(key=lambda x: x.get("valoracion", 0), reverse=True)

    logger.info("✅ Renderizando template con %s productos finales", len(products))
    return render_template("collection.html", products=products, page=page)
