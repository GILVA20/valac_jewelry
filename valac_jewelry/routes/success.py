from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app
success_bp = Blueprint('success', __name__)

@success_bp.route('/success', methods=['GET'])
def success():
    # Recupera la orden y sus ítems de la sesión
    order = session.get("order_data")
    order_items = session.get("order_items", [])
    
    if not order:
        flash("No se encontró información de la orden.", "error")
        current_app.logger.error("SUCCESS: order_data es None, redirigiendo a home.")
        return redirect(url_for("main.home"))
    
    order_id = order.get("id")
    if order_id:
        try:
            supabase = current_app.supabase
            update_data = {"estado_pago": "Completado"}
            # Realizamos el update sin encadenar select
            response = supabase.table("orders").update(update_data).eq("id", order_id).execute()
            current_app.logger.debug("SUCCESS: Respuesta del update para orden %s: %s", order_id, response)
            
            # Consultamos la orden actualizada sin usar .single()
            query_response = supabase.table("orders").select().eq("id", order_id).execute()
            current_app.logger.debug("SUCCESS: Respuesta de query para orden %s: %s", order_id, query_response)
            
            if query_response.data and isinstance(query_response.data, list) and len(query_response.data) > 0:
                updated_order = query_response.data[0]
                current_app.logger.debug("SUCCESS: Orden actualizada: %s", updated_order)
                order["estado_pago"] = updated_order.get("estado_pago", "Pendiente")
                session["order_data"] = order
            else:
                current_app.logger.error("SUCCESS: El update no devolvió datos esperados para la orden %s: %s", order_id, response)
                flash("No se pudo actualizar el estado de pago en la base de datos.", "error")
        except Exception as e:
            current_app.logger.error("SUCCESS: Excepción al actualizar la orden %s: %s", order_id, e)
            flash("Error al actualizar el estado de pago.", "error")
        # Forzamos que en la sesión aparezca "Completado" para mostrar el resumen
        order["estado_pago"] = "Completado"
        session["order_data"] = order

    current_app.logger.debug("SUCCESS: Renderizando success.html para la orden con ID: %s", order.get("id"))
    return render_template('success.html', order=order, order_items=order_items)
