from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app

pending_bp = Blueprint('pending', __name__)

@pending_bp.route('/pending', methods=['GET'])
def pending():
    # Recupera la orden de la sesión
    order = session.get("order_data")
    
    if not order:
        flash("No se encontró información de la orden pendiente.", "error")
        current_app.logger.error("PENDING: order_data es None, redirigiendo a home.")
        return redirect(url_for("main.home"))
    
    order_id = order.get("id")
    if order_id:
        try:
            supabase = current_app.supabase
            # Solo actualizamos si no está ya como "Pendiente"
            if order.get("estado_pago") != "Pendiente":
                response = supabase.table("orders").update({"estado_pago": "Pendiente"}).eq("id", order_id).execute()
                current_app.logger.debug("PENDING: Orden marcada como pendiente: %s", response)
                
                # Actualizamos la sesión
                order["estado_pago"] = "Pendiente"
                session["order_data"] = order
        except Exception as e:
            current_app.logger.error("PENDING: Error al actualizar orden %s: %s", order_id, e)
            flash("Error al registrar el estado pendiente.", "warning")  # Warning porque el pago podría aprobarse después

    return render_template('pending.html', order=order)