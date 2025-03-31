from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/track/<int:order_id>', methods=['GET'])
def track(order_id):
    current_app.logger.debug("ORDERS.TRACK: Iniciando seguimiento para order_id: %s", order_id)
    supabase = current_app.supabase
    try:
        response = supabase.table("orders").select("*").eq("id", order_id).execute()
        current_app.logger.debug("ORDERS.TRACK: Respuesta de query para orden %s: %s", order_id, response)
    except Exception as e:
        current_app.logger.error("ORDERS.TRACK: Excepción al consultar la orden %s: %s", order_id, e)
        flash("Error al consultar la orden.", "error")
        return redirect(url_for("main.home"))
    if not response.data or len(response.data) == 0:
        current_app.logger.error("ORDERS.TRACK: No se encontró la orden con id: %s", order_id)
        flash("Orden no encontrada.", "error")
        return redirect(url_for("main.home"))
    order = response.data[0]
    # Si lo deseas, actualiza la información en la sesión (similar a success.py)
    session["order_data"] = order
    return render_template('order_track.html', order=order)
