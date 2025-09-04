# routes/pending.py
from flask import Blueprint, render_template, session, flash, redirect, url_for
from .success import _to_float, _get_shipping  # reutilizamos helpers

pending_bp = Blueprint('pending', __name__)

@pending_bp.route('/pending', methods=['GET'])
def pending():
    order = session.get("order_data")
    cart_snapshot = session.get("cart_snapshot")

    if not order or not cart_snapshot:
        flash("No se encontró información de la orden en pendiente.", "error")
        return redirect(url_for("main.home"))

    # Totales 100% desde snapshot
    order["subtotal"] = _to_float(cart_snapshot.get("subtotalProducts"))
    order["discount"] = _to_float(cart_snapshot.get("discount_total"))
    order["total"]    = _to_float(cart_snapshot.get("total"))
    order["shipping"] = _get_shipping(cart_snapshot, order)
    order["estado_pago"] = "Pendiente"

    return render_template('pending.html', order=order, cart_snapshot=cart_snapshot)
