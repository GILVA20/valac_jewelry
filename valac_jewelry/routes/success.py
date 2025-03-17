import os
from datetime import datetime
from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app

success_bp = Blueprint('success', __name__)

@success_bp.route('/success')
def success():
    """
    Endpoint que se invoca cuando MercadoPago redirige al usuario tras un pago aprobado.
    Extrae de la sesión los datos reales de la orden y la lista de ítems,
    registra la orden en la base de datos usando Supabase, limpia la sesión
    y renderiza un resumen de la orden exitosa.
    """
    # Extraer datos de la orden e ítems desde la sesión
    order_data = session.get("order_data")
    order_items = session.get("order_items")
    
    if not order_data or not order_items:
        flash("No se encontraron datos de la orden. Por favor, completa el proceso de compra nuevamente.", "error")
        return redirect(url_for('checkout.checkout'))
    
    # Agregar la fecha actual al pedido (en formato ISO)
    order_data["fecha_pedido"] = datetime.utcnow().isoformat()
    # Si el usuario está autenticado, podrías agregar:
    # order_data["user_id"] = session.get("user_id")
    
    # Registrar la orden en la base de datos usando el cliente de Supabase
    orders_response = current_app.supabase.table("orders").insert(order_data).execute()
    if orders_response.error:
        flash("Error al registrar la orden en la base de datos.", "error")
        return redirect(url_for('checkout.checkout'))
    
    # Obtener el ID de la orden recién creada
    order_id = orders_response.data[0]["id"]
    
    # Registrar cada ítem de la orden en la tabla "order_items", asociándolo al order_id
    for item in order_items:
        item["order_id"] = order_id
        response_item = current_app.supabase.table("order_items").insert(item).execute()
        if response_item.error:
            flash("Error al registrar algunos ítems de la orden.", "error")
            # Aquí podrías manejar un rollback o notificar al administrador según tu lógica
    
    # Limpiar los datos de la sesión relacionados a la orden
    session.pop("order_data", None)
    session.pop("order_items", None)
    
    # Renderizar la plantilla del resumen de la orden exitosa
    return render_template("order_summary.html", order=order_data, order_items=order_items, order_id=order_id)
