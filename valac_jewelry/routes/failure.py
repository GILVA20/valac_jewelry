from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app

failure_bp = Blueprint('failure', __name__)

@failure_bp.route('/failure', methods=['GET'])
def failure():
    order = session.get("order_data")
    
    if not order:
        flash("No se encontró información de la orden fallida.", "error")
        return redirect(url_for("main.home"))
    
    order_id = order.get("id")
    if order_id:
        try:
            supabase = current_app.supabase
            # Marcamos como fallido solo si no está ya en ese estado
            if order.get("estado_pago") != "Fallido":
                response = supabase.table("orders").update({
                    "estado_pago": "Fallido",
                    "motivo_fallo": "Rechazado por la pasarela de pago"
                }).eq("id", order_id).execute()
                
                current_app.logger.debug("FAILURE: Orden marcada como fallida: %s", response)
                order["estado_pago"] = "Fallido"
                session["order_data"] = order
        except Exception as e:
            current_app.logger.error("FAILURE: Error al actualizar orden %s: %s", order_id, e)
            flash("Error al registrar el pago fallido.", "error")

    return render_template('failure.html', order=order)