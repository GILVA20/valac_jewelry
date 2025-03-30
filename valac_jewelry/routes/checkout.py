import os
import time
import logging
from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, session
import mercadopago
from supabase import create_client, Client

def sanitize_input(input_str):
    # Sanitización básica: recorta espacios y escapa caracteres HTML
    return str(input_str).strip().replace("<", "&lt;").replace(">", "&gt;")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

checkout_bp = Blueprint('checkout', __name__)

def build_order_items_and_subtotal():
    """
    Construye la lista de ítems de la orden consultando Supabase para cada producto
    y calcula el subtotal basado en el precio y cantidad.
    Se asume que el carrito está almacenado en session["cart"] como un diccionario {producto_id (str): cantidad}.
    """
    cart_data = session.get("cart", {})
    order_items = []
    subtotal = 0.0
    for product_id_str, quantity in cart_data.items():
        try:
            product_id = int(product_id_str)
            resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
            if resp.data:
                product = resp.data
                # Asignar la cantidad y asegurar que existan campos necesarios
                product['cantidad'] = int(quantity)
                # Si faltan detalles, se pueden agregar campos vacíos
                product.setdefault("descripcion", "Sin descripción")
                price = float(product.get("precio", 0))
                subtotal += price * int(quantity)
                order_items.append(product)
            else:
                current_app.logger.error("Producto con ID %s no encontrado.", product_id)
        except Exception as e:
            current_app.logger.error("Error obteniendo producto %s: %s", product_id_str, e)
    return order_items, subtotal

def create_order_in_db(order_data, order_items):
    """
    Inserta la orden en Supabase y devuelve el ID de la orden.
    Si no se inserta correctamente, registra el error.
    """
    response = supabase.table("orders").insert(order_data).execute()
    if not response.data:
        current_app.logger.error("Error insertando la orden: %s", response)
        return None
    order_id = response.data[0]["id"]
    order_data["id"] = order_id
    # Guardamos la orden y sus ítems en la sesión para mostrarlos en la vista de éxito
    session["order_data"] = order_data
    session["order_items"] = order_items
    return order_id

@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'GET':
        return render_template('checkout.html')
    
    # Extraer y sanitizar datos del formulario
    nombre = sanitize_input(request.form.get('nombre'))
    direccion_envio = sanitize_input(request.form.get('direccion'))
    estado_envio = sanitize_input(request.form.get('estado'))
    colonia = sanitize_input(request.form.get('colonia'))
    ciudad = sanitize_input(request.form.get('ciudad'))
    codigo_postal = sanitize_input(request.form.get('codigo_postal'))
    telefono = sanitize_input(request.form.get('telefono'))
    email = sanitize_input(request.form.get('email'))
    
    # Extraer el método de pago (se permite 'mock_gateway')
    metodo_pago = request.form.get('metodo_pago', '').strip().lower()
    if metodo_pago == "mercadopago":
        metodo_pago = "MercadoPago"
    elif metodo_pago == "aplazo":
        metodo_pago = "aplazo"
    elif metodo_pago == "mock_gateway":
        metodo_pago = "mock_gateway"
    metodo_pago = sanitize_input(metodo_pago)
    
    # Mapear abreviaturas a nombre completo (por ejemplo, "hi" a "Hidalgo")
    estado_mapping = {"hi": "Hidalgo", "hidalgo": "Hidalgo"}
    estado_geografico = estado_mapping.get(estado_envio.lower(), estado_envio)
    
    # Validar que se hayan completado todos los campos obligatorios
    if not all([nombre, direccion_envio, estado_geografico, colonia, ciudad, codigo_postal, telefono, email, metodo_pago]):
        flash("Por favor, completa todos los campos obligatorios.", "error")
        return redirect(url_for('checkout.checkout'))
    
    current_app.logger.debug("Datos del checkout: nombre=%s, direccion=%s, estado_geografico=%s, colonia=%s, ciudad=%s, cp=%s, telefono=%s, email=%s, metodo_pago=%s",
                               nombre, direccion_envio, estado_geografico, colonia, ciudad, codigo_postal, telefono, email, metodo_pago)
    
    # Construir la lista de ítems de la orden y calcular el subtotal dinámicamente
    order_items, subtotal = build_order_items_and_subtotal()
    current_app.logger.debug("Ítems de orden obtenidos: %s", order_items)
    current_app.logger.debug("Subtotal calculado: %s", subtotal)
    
    # Si no hay ítems en el carrito, abortamos
    if not order_items:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for('cart.view_cart'))
    
    shipping_cost = 1.0  # Costo fijo simulado de envío
    total = subtotal + shipping_cost
    current_app.logger.debug("Costo de envío: %s, Total calculado: %s", shipping_cost, total)
    
    # Preparar los datos de la orden
    order_data = {
        "nombre": nombre,
        "dirección_envío": direccion_envio,
        "estado_geografico": estado_geografico,
        "colonia": colonia,
        "ciudad": ciudad,
        "codigo_postal": codigo_postal,
        "telefono": telefono,
        "email": email,
        "método_pago": metodo_pago,
        "subtotal": subtotal,
        "costo_envío": shipping_cost,
        "total": total,
        "estado_pago": "Pendiente"  # Estado inicial de la orden
    }
    
    current_app.logger.debug("Datos de orden: %s", order_data)
    
    # Registrar la orden en Supabase
    order_id = create_order_in_db(order_data, order_items)
    if not order_id:
        flash("Error registrando la orden.", "error")
        return redirect(url_for('checkout.checkout'))
    current_app.logger.debug("Orden registrada con ID: %s", order_id)
    
    # Validar método de pago
    if metodo_pago not in ["MercadoPago", "aplazo", "mock_gateway"]:
        flash("Método de pago no válido. Selecciona MercadoPago, Aplazo o Pago Simulado.", "error")
        return redirect(url_for('checkout.checkout'))
    
    if metodo_pago == "MercadoPago":
        simular_pago = os.environ.get("SIMULAR_PAGO", "False").lower() == "true"
        current_app.logger.debug("Método MercadoPago seleccionado. SIMULAR_PAGO: %s", simular_pago)
        if simular_pago:
            simulated_status = {
                "estado_pago": "Completado",
                "transaction_id": "SIMULADO",
                "fecha_actualizacion": "now()"
            }
            response = supabase.table("orders").update(simulated_status).eq("id", order_id).execute()
            current_app.logger.debug("Respuesta de simulación: %s", response)
            if not response.data:
                flash("Error al simular el pago.", "error")
                return redirect(url_for('checkout.checkout'))
            flash("Pago simulado con éxito. Orden completada.", "success")
            return redirect(url_for('success.success'))
        else:
            current_app.logger.debug("Iniciando integración real con MercadoPago")
            ENV = os.getenv("FLASK_ENV", "development").lower()
            IS_PROD = ENV == "production"
            token = current_app.config["MP_ACCESS_TOKEN"]
            current_app.logger.debug("Token seleccionado: %s", token)
            mp = mercadopago.SDK(token)
            back_urls = {
                "success": url_for('success.success', _external=True),
                "failure": url_for('failure.failure', _external=True),
                "pending": url_for('pending.pending', _external=True)
            }
            notification_url = "https://valacjoyas.com/webhook"  # URL válida para notificaciones
            preference_data = {
                "items": [{
                    "title": "Orden de Compra VALAC Joyas",
                    "unit_price": total,
                    "quantity": 1
                }],
                "back_urls": back_urls,
                "auto_return": "approved",
                "notification_url": notification_url,
                "metadata": {"environment": "test"}
            }
            current_app.logger.debug("Datos para preferencia: %s", preference_data)
            preference_response = mp.preference().create(preference_data)
            current_app.logger.debug("Respuesta de preferencia: %s", preference_response)
            if not preference_response or "response" not in preference_response:
                current_app.logger.error("Respuesta inválida de MercadoPago: %s", preference_response)
                flash("Error en la respuesta de MercadoPago, por favor inténtalo nuevamente.", "error")
                return redirect(url_for('checkout.checkout'))
            preference = preference_response["response"]
            if "id" not in preference:
                current_app.logger.error("Error: La preferencia no contiene 'id'. Respuesta: %s", preference)
                flash("Error al crear la preferencia de pago.", "error")
                return redirect(url_for('checkout.checkout'))
            preference_id = preference["id"]
            current_app.logger.debug("Preferencia creada con ID: %s", preference_id)
            return render_template("mercadopago_checkout.html",
                                   preference_id=preference_id,
                                   MP_PUBLIC_KEY=current_app.config["MP_PUBLIC_KEY"],
                                   sandbox=(not IS_PROD))
    elif metodo_pago == "aplazo":
        # Lógica simulada para Aplazo
        pago_exitoso = True  # Simulación fija
        current_app.logger.debug("Método Aplazo seleccionado. Pago exitoso simulación: %s", pago_exitoso)
        if pago_exitoso:
            flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
            return redirect(url_for('success.success'))
        else:
            flash("Error al procesar el pago. Intenta nuevamente.", "error")
            return redirect(url_for('checkout.checkout'))
    elif metodo_pago == "mock_gateway":
        # Método de pago simulado: redirige a la vista de simulación
        return redirect(url_for('mock_checkout.index', order_id=order_id))
    
    return render_template('checkout.html')
