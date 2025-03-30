from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

mock_checkout_bp = Blueprint('mock_checkout', __name__, url_prefix='/mock-checkout')

@mock_checkout_bp.route('/', methods=['GET'])
def index():
    order_id = request.args.get('order_id')
    current_app.logger.debug("MOCK_CHECKOUT INDEX: order_id recibido: %s", order_id)
    if not order_id:
        flash("No se proporcionó ID de orden.", "error")
        current_app.logger.error("MOCK_CHECKOUT INDEX: Falta order_id, redirigiendo a home.")
        return redirect(url_for('main.home'))
    return render_template("mock_checkout.html", order_id=order_id)

@mock_checkout_bp.route('/simulate', methods=['POST'])
def simulate():
    order_id = request.form.get('order_id')
    status = request.form.get('status')
    current_app.logger.debug("MOCK_CHECKOUT SIMULATE: Iniciando simulación para order_id=%s, status=%s", order_id, status)
    
    if not order_id:
        flash("ID de orden no proporcionado.", "error")
        current_app.logger.error("MOCK_CHECKOUT SIMULATE: order_id no proporcionado, redirigiendo a home.")
        return redirect(url_for('main.home'))
    
    # Definir el nuevo estado según el botón presionado
    update_data = {}
    if status == "success":
        update_data["estado_pago"] = "Completado"
    elif status == "pending":
        update_data["estado_pago"] = "Pendiente"
    elif status == "failure":
        update_data["estado_pago"] = "Fallido"
    else:
        flash("Estado de simulación no válido.", "error")
        current_app.logger.error("MOCK_CHECKOUT SIMULATE: Estado no válido recibido: %s", status)
        return redirect(url_for('main.home'))
    
    try:
        supabase = current_app.supabase
        response = supabase.table("orders").update(update_data).eq("id", int(order_id)).execute()
        current_app.logger.debug("MOCK_CHECKOUT SIMULATE: Respuesta del update: %s", response)
    except Exception as e:
        current_app.logger.error("MOCK_CHECKOUT SIMULATE: Excepción durante el update para la orden %s: %s", order_id, e)
        flash("Excepción al procesar la simulación de pago.", "error")
        return redirect(url_for("checkout.checkout"))
    
    try:
        query_response = supabase.table("orders").select().eq("id", int(order_id)).execute()
        current_app.logger.debug("MOCK_CHECKOUT SIMULATE: Respuesta de query para orden %s: %s", order_id, query_response)
    except Exception as e:
        current_app.logger.error("MOCK_CHECKOUT SIMULATE: Excepción al consultar la orden %s: %s", order_id, e)
        flash("Excepción al consultar la orden actualizada.", "error")
        return redirect(url_for("checkout.checkout"))
    
    if not query_response.data or len(query_response.data) == 0:
        current_app.logger.error("MOCK_CHECKOUT SIMULATE: No se encontró la orden actualizada para %s", order_id)
        flash("Error actualizando la orden simulada.", "error")
        return redirect(url_for("checkout.checkout"))
    else:
        updated_order = query_response.data[0]
        current_app.logger.debug("MOCK_CHECKOUT SIMULATE: Orden actualizada: %s", updated_order)
        order = session.get("order_data")
        if order and str(order.get("id")) == str(order_id):
            order["estado_pago"] = updated_order.get("estado_pago", "Pendiente")
            session["order_data"] = order
            current_app.logger.debug("MOCK_CHECKOUT SIMULATE: order_data actualizado en sesión: %s", order)
        else:
            current_app.logger.error("MOCK_CHECKOUT SIMULATE: order_data no encontrada en sesión o no coincide con order_id.")
            flash("La orden no se encuentra en la sesión.", "error")
            return redirect(url_for("checkout.checkout"))
    
    flash("Simulación de pago procesada.", "success")
    current_app.logger.debug("MOCK_CHECKOUT SIMULATE: Preparando redirección según status: %s", status)

    # Seleccionar la ruta de destino según el estado simulado
    if status == "success":
        target_endpoint = "success.success"
    elif status == "pending":
        target_endpoint = "pending.pending"
    elif status == "failure":
        target_endpoint = "failure.failure"
    else:
        target_endpoint = "main.home"

    target_url = url_for(target_endpoint, _external=True)
    current_app.logger.debug("MOCK_CHECKOUT SIMULATE: URL generada para redirección: %s", target_url)

    if not target_url:
        current_app.logger.error("La ruta %s no existe. Redirigiendo a home.", target_endpoint)
        return redirect(url_for("main.home"))

    return redirect(target_url)
