import os
from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, session
import mercadopago
from supabase import create_client, Client  # Asegurate de tener instalado supabase-py

def sanitize_input(input_str):
    # Sanitización básica: recorta espacios y escapa caracteres HTML
    return str(input_str).strip().replace("<", "&lt;").replace(">", "&gt;")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

checkout_bp = Blueprint('checkout', __name__)

def create_order_in_db(order_data, order_items):
    """
    Inserta la orden en Supabase. Se asume que la tabla "orders" tiene las siguientes columnas:
      - nombre
      - dirección_envío
      - estado_geografico
      - colonia
      - ciudad
      - codigo_postal
      - telefono
      - email
      - método_pago
      - subtotal
      - costo_envío
      - total
      - estado_pago
    Además, "id" es autogenerado.
    """
    response = supabase.table("orders").insert(order_data).execute()
    res = response.dict()  # Convertimos a diccionario para acceder de forma segura
    if res.get("error"):
        print("Error insertando la orden:", res["error"])
        return None
    order_id = res["data"][0]["id"]
    order_data["id"] = order_id
    session["order_data"] = order_data  # Para prellenar en caso de reintentos
    session["order_items"] = order_items
    return order_id

@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Extraer datos del formulario
        nombre = request.form.get('nombre')
        direccion_envio = request.form.get('direccion')
        estado_envio = request.form.get('estado')
        colonia = request.form.get('colonia')
        ciudad = request.form.get('ciudad')
        codigo_postal = request.form.get('codigo_postal')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        mp_val = request.form.get('metodo_pago') or ""
        metodo_pago = sanitize_input(mp_val)
        if metodo_pago:
            metodo_pago = "MercadoPago" if metodo_pago.lower() == "mercadopago" else metodo_pago

        # Sanitizar el resto de los campos
        nombre = sanitize_input(nombre)
        direccion_envio = sanitize_input(direccion_envio)
        estado_envio = sanitize_input(estado_envio)
        colonia = sanitize_input(colonia)
        ciudad = sanitize_input(ciudad)
        codigo_postal = sanitize_input(codigo_postal)
        telefono = sanitize_input(telefono)
        email = sanitize_input(email)
        
        # Mapear abreviaturas a nombre completo (ejemplo)
        estado_mapping = {"HI": "Hidalgo"}
        estado_geografico = estado_mapping.get(estado_envio, estado_envio)
        
        # Validar campos obligatorios
        if not all([nombre, direccion_envio, estado_geografico, colonia, ciudad, codigo_postal, telefono, email, metodo_pago]):
            flash("Por favor, completa todos los campos obligatorios.", "error")
            return redirect(url_for('checkout.checkout'))
        
        current_app.logger.debug("Datos del checkout: nombre=%s, direccion=%s, estado_geografico=%s, colonia=%s, ciudad=%s, cp=%s, telefono=%s, email=%s, metodo_pago=%s",
                                   nombre, direccion_envio, estado_geografico, colonia, ciudad, codigo_postal, telefono, email, metodo_pago)
        
        # Calcular subtotal y costo de envío (simulado)
        subtotal = 5000.00  
        shipping_cost = 1 if subtotal >= 6000 else 1
        total = subtotal + shipping_cost
        current_app.logger.debug("Subtotal: %s, Costo de envío: %s, Total: %s", subtotal, shipping_cost, total)
        
        # Preparar datos de la orden
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
            "estado_pago": "Pendiente"  # Estado del pedido
        }

        order_items = session.get("cart_items", [])
        current_app.logger.debug("Datos de orden: %s", order_data)
        current_app.logger.debug("Items de orden: %s", order_items)
        
        # Registrar la orden en Supabase
        order_id = create_order_in_db(order_data, order_items)
        if not order_id:
            flash("Error registrando la orden.", "error")
            return redirect(url_for('checkout.checkout'))
        current_app.logger.debug("Orden registrada con ID: %s", order_id)
        
        # Validar método de pago
        if metodo_pago not in ["MercadoPago", "aplazo"]:
            flash("Método de pago no válido. Selecciona MercadoPago o aplazo.", "error")
            return redirect(url_for('checkout.checkout'))
        
        if metodo_pago == "MercadoPago":
            simular_pago = os.environ.get("SIMULAR_PAGO", "False").lower() == "true"
            current_app.logger.debug("Método MercadoPago seleccionado. SIMULAR_PAGO: %s", simular_pago)
            if simular_pago:
                current_app.logger.debug("Simulando pago para order_id: %s", order_id)
                simulated_status = {
                    "estado_pago": "Completado",
                    "transaction_id": "SIMULADO",
                    "fecha_actualizacion": "now()"
                }
                response = supabase.table("orders").update(simulated_status).eq("id", order_id).execute()
                current_app.logger.debug("Respuesta de simulación: %s", response)
                if response.dict().get("error"):
                    flash("Error al simular el pago.", "error")
                    return redirect(url_for('checkout.checkout'))
                flash("Pago simulado con éxito. Orden completada.", "success")
                return redirect(url_for('success.success'))
            else:
                current_app.logger.debug("Iniciando integración real con MercadoPago")
                ENV = os.getenv("FLASK_ENV", "development").lower()
                IS_PROD = ENV == "production"
                token = current_app.config["MP_ACCESS_TOKEN"]
                current_app.logger.debug("DEBUG: ENV: %s, IS_PROD: %s", ENV, IS_PROD)
                current_app.logger.debug("DEBUG: Token seleccionado: %s", token)
                mp = mercadopago.SDK(token)
                
                preference_data = {
                    "items": [{
                        "title": "Orden de Compra VALAC Joyas",
                        "unit_price": total,
                        "quantity": 1
                    }],
                    "external_reference": str(order_id),
                    "back_urls": {
                        "success": "https://valacjoyas.com/success",
                        "failure": "https://valacjoyas.com/failure",
                        "pending": "https://valacjoyas.com/pending"
                    },
                    "auto_return": "approved",
                    "notification_url": "https://valacjoyas.com/webhook"
                }
                if not IS_PROD:
                    preference_data.setdefault("metadata", {}).update({"environment": "test"})
                    current_app.logger.debug("DEBUG: Preference data updated for test environment: %s", preference_data)
                
                current_app.logger.debug("Datos para preferencia: %s", preference_data)
                preference_response = mp.preference().create(preference_data)
                current_app.logger.debug("DEBUG: Respuesta de preferencia: %s", preference_response)
                if not preference_response or "response" not in preference_response:
                    current_app.logger.error("DEBUG: Respuesta inválida de MercadoPago: %s", preference_response)
                    flash("Error en la respuesta de MercadoPago, por favor inténtalo nuevamente.", "error")
                    return redirect(url_for('checkout.checkout'))
                preference = preference_response["response"]
                preference_id = preference["id"]
                current_app.logger.debug("DEBUG: Preferencia creada con ID: %s", preference_id)
                
                return render_template(
                    "mercadopago_checkout.html",
                    preference_id=preference_id,
                    MP_PUBLIC_KEY=current_app.config["MP_PUBLIC_KEY"],
                    sandbox=(not IS_PROD)
                )
        else:
            pago_exitoso = True  # Simulación del pago para "aplazo"
            current_app.logger.debug("Método aplazo seleccionado. Pago exitoso simulación: %s", pago_exitoso)
            if pago_exitoso:
                flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
                return redirect(url_for('success.success'))
            else:
                flash("Error al procesar el pago. Intenta nuevamente.", "error")
                return redirect(url_for('checkout.checkout'))
    
    return render_template('checkout.html')
