import os
from datetime import datetime
from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app
import logging

success_bp = Blueprint('success', __name__)

@success_bp.route('/success')
def success():
    """
    Se invoca cuando MercadoPago redirige al usuario tras un pago aprobado.
    Extrae los datos de la orden e ítems desde la sesión, registra la orden en la BD
    y renderiza el resumen de la compra.
    """
    order_data = session.get("order_data")
    order_items = session.get("order_items")
    
    if not order_data or not order_items:
        flash("No se encontraron datos de la orden. Por favor, completa el proceso de compra nuevamente.", "error")
        return redirect(url_for('checkout.checkout'))
    
    order_data["fecha_pedido"] = datetime.utcnow().isoformat()
    # ✨ ADDITIONS ✨: Filtrar order_data para solo incluir columnas válidas en la tabla orders
    allowed_keys = {"nombre", "dirección_envío", "estado", "colonia", "método_pago", "total", "estado_pago", "fecha_pedido"}
    order_data_db = {k: order_data[k] for k in order_data if k in allowed_keys}
    current_app.logger.debug("DEBUG: Datos de orden filtrados para BD en success: %s", order_data_db)
    
    # Registrar la orden en la BD
    orders_response = current_app.supabase.table("orders").insert(order_data_db).execute()
    if orders_response.error:
        flash("Error al registrar la orden en la base de datos.", "error")
        return redirect(url_for('checkout.checkout'))
    
    order_id = orders_response.data[0]["id"]
    
    # Registrar cada ítem en order_items
    for item in order_items:
        item["order_id"] = order_id
        response_item = current_app.supabase.table("order_items").insert(item).execute()
        if response_item.error:
            flash("Error al registrar algunos ítems de la orden.", "error")
            current_app.logger.error("Error registrando ítem %s: %s", item, response_item.error)
    
    session.pop("order_data", None)
    session.pop("order_items", None)
    
    # Renderiza la plantilla de resumen
    return render_template("order_summary.html", order=order_data, order_items=order_items, order_id=order_id)
