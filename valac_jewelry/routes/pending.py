from datetime import datetime
from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app

pending_bp = Blueprint('pending', __name__)

@pending_bp.route('/pending')
def pending():
    """
    Se invoca cuando el pago está en proceso.
    Se registra la orden con estado de pago 'Pendiente' y se muestra una página informativa.
    """
    order_data = session.get("order_data")
    order_items = session.get("order_items")
    
    if not order_data or not order_items:
        flash("No se encontraron datos de la orden. Por favor, completa el proceso de compra nuevamente.", "error")
        return redirect(url_for('checkout.checkout'))
    
    # Actualizamos la fecha del pedido y establecemos estado de pago "Pendiente"
    order_data["fecha_pedido"] = datetime.utcnow().isoformat()
    order_data["estado_pago"] = "Pendiente"
    
    orders_response = current_app.supabase.table("orders").insert(order_data).execute()
    if orders_response.error:
        flash("Error al registrar la orden en la base de datos.", "error")
        return redirect(url_for('checkout.checkout'))
    
    order_id = orders_response.data[0]["id"]
    
    for item in order_items:
        item["order_id"] = order_id
        response_item = current_app.supabase.table("order_items").insert(item).execute()
        if response_item.error:
            flash("Error al registrar algunos ítems de la orden.", "error")
    
    session.pop("order_data", None)
    session.pop("order_items", None)
    
    return render_template("pago_en_proceso.html", order_data=order_data, order_id=order_id)
