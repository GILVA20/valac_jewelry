import logging
from flask import Blueprint, render_template, current_app

anillos_bp = Blueprint("anillos_compromiso", __name__)
logger = logging.getLogger(__name__)

WHATSAPP_NUMBER = "5213320471076"


@anillos_bp.route("/anillos-compromiso")
def anillos_compromiso():
    sb = current_app.supabase
    try:
        resp = (
            sb.table("products")
            .select(
                "id, nombre, descripcion, precio, descuento_pct, precio_descuento, "
                "tipo_producto, genero, tipo_oro, imagen, stock_total, created_at, "
                "product_images ( imagen, orden, object_position )"
            )
            .eq("activo", True)
            .eq("tipo_producto", "Anillos de Compromiso")
            .order("created_at", desc=True)
            .execute()
        )
        products = resp.data or []
    except Exception as exc:
        logger.exception("Error cargando anillos de compromiso: %s", exc)
        products = []

    return render_template(
        "anillos_compromiso.html",
        products=products,
        whatsapp_number=WHATSAPP_NUMBER,
    )
