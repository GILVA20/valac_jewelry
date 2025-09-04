# routes/failure.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app
from .success import _to_float, _get_shipping  # reutilizamos helpers

failure_bp = Blueprint('failure', __name__)

@failure_bp.route('/failure', methods=['GET'])
def failure():
    order = session.get("order_data")
    cart_snapshot = session.get("cart_snapshot")

    if not order:
        flash("No se encontró información de la orden fallida.", "error")
        return redirect(url_for("main.home"))

    # Si hay snapshot, usarlo como fuente de verdad para mostrar totales.
    if cart_snapshot:
        order["subtotal"] = _to_float(cart_snapshot.get("subtotalProducts"))
        order["discount"] = _to_float(cart_snapshot.get("discount_total"))
        order["total"]    = _to_float(cart_snapshot.get("total"))
        order["shipping"] = _get_shipping(cart_snapshot, order)
    else:
        # fallback defensivo si no hay snapshot
        order["subtotal"] = _to_float(order.get("subtotal"))
        order["discount"] = _to_float(order.get("discount"))
        order["total"]    = _to_float(order.get("total"))
        order["shipping"] = _get_shipping({}, order)

    order["estado_pago"] = "Fallido"

    current_app.logger.debug(
        "FAILURE Render: id=%s subtotal=%.2f discount=%.2f shipping=%.2f total=%.2f",
        order.get("id"), order["subtotal"], order["discount"], order["shipping"], order["total"]
    )

    return render_template('failure.html', order=order, cart_snapshot=cart_snapshot)
