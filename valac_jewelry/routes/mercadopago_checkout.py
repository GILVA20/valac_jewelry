import os
import logging
from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for
import mercadopago
from supabase import create_client, Client  # Asegúrate de tener instalado supabase-py

# ✨ ADDITIONS ✨
ENV = os.getenv("FLASK_ENV", "development").lower()  # DEBUG: Capturing environment in mercadopago_checkout
IS_PROD = ENV == "production"  # DEBUG: Production environment flag in mercadopago_checkout
logging.debug("DEBUG: In mercadopago_checkout: ENV=%s, IS_PROD=%s", ENV, IS_PROD)

# ✨ ADDITIONS ✨
def sanitize_input(input_str):
    return str(input_str).strip().replace("<", "&lt;").replace(">", "&gt;")
# DEBUG: Added sanitization function in mercadopago_checkout

# Configuración de MercadoPago: se selecciona el token según el entorno
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN_PROD" if IS_PROD else "MP_ACCESS_TOKEN_TEST")
MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY_PROD" if IS_PROD else "MP_PUBLIC_KEY_TEST")
logging.debug("DEBUG: MP_ACCESS_TOKEN utilizado: %s", MP_ACCESS_TOKEN)
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
logging.debug("DEBUG: SUPABASE_URL: %s", SUPABASE_URL)
logging.debug("DEBUG: SUPABASE_KEY: %s", SUPABASE_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

mp_checkout_bp = Blueprint('mp_checkout', __name__)

@mp_checkout_bp.route('/create_preference', methods=['POST'])
def create_preference():
    """
    Endpoint para crear una preferencia de pago.
    Se espera recibir un JSON con la llave "items", que es una lista de objetos con: title, unit_price y quantity.
    """
    try:
        data = request.get_json()
        logging.debug("DEBUG: Datos recibidos en create_preference: %s", data)
        # ✨ ADDITIONS ✨
        if "items" in data:
            sanitized_items = []
            for item in data["items"]:
                sanitized_item = {k: sanitize_input(v) if isinstance(v, str) else v for k, v in item.items()}
                sanitized_items.append(sanitized_item)
            data["items"] = sanitized_items
            logging.debug("DEBUG: Items sanitizados: %s", data["items"])
        
        if not data or "items" not in data:
            logging.debug("DEBUG: No se proporcionaron items en la solicitud")
            return jsonify({"error": "No se proporcionaron items"}), 400

        items = data["items"]
        logging.debug("DEBUG: Items recibidos: %s", items)

        preference_data = {
            "items": items,
            "back_urls": {
                "success": "https://valacjoyas.com/success",
                "failure": "https://valacjoyas.com/failure",
                "pending": "https://valacjoyas.com/pending"
            },
            "auto_return": "approved",
            "notification_url": "https://valacjoyas.com/webhook"
        }
        logging.debug("DEBUG: Datos de preferencia a crear: %s", preference_data)

        # ✨ ADDITIONS ✨: Reinstanciar el SDK con el token adecuado según el entorno
        # La configuración de la app ya ha asignado MP_ACCESS_TOKEN correctamente según el entorno.
        token = current_app.config["MP_ACCESS_TOKEN"]
        logging.debug("DEBUG: Token seleccionado: %s", token)
        mp = mercadopago.SDK(token)
        
        # ✨ ADDITIONS ✨: Si no es producción, agregar metadata para marcar ambiente de prueba
        if not IS_PROD:
            preference_data.setdefault("metadata", {}).update({"environment": "test"})
            logging.debug("DEBUG: Preference data updated for test environment: %s", preference_data)
        
        logging.debug("Datos para preferencia: %s", preference_data)
        preference_response = mp.preference().create(preference_data)
        logging.debug("DEBUG: Respuesta de la creación de preferencia: %s", preference_response)
        if not preference_response or "response" not in preference_response:
            logging.error("DEBUG: Respuesta inválida de MercadoPago: %s", preference_response)
            flash("Error en la respuesta de MercadoPago, por favor inténtalo nuevamente.", "error")
            return redirect(url_for('checkout.checkout'))
        preference = preference_response["response"]
        logging.debug("DEBUG: Preferencia creada: %s", preference)
        preference_id = preference["id"]
        logging.debug("DEBUG: Preferencia creada con ID: %s", preference_id)
        return jsonify({"id": preference_id}), 200
    except Exception as e:
        logging.exception("DEBUG: Error al crear preferencia:")
        return jsonify({"error": str(e)}), 500

@mp_checkout_bp.route('/webhook', methods=['POST'])
def webhook():
    try:
        # ✨ ADDITIONS ✨: Validar firma del webhook
        signature = request.headers.get("X-MercadoPago-Signature", "")
        expected_signature = os.getenv("MP_WEBHOOK_SECRET", "default_secret")
        if signature != expected_signature:
            logging.error("DEBUG: Firma de webhook inválida: %s", signature)
            return "Firma inválida", 403
        # ✨ ADDITIONS ✨: Aquí se puede agregar prevención contra ataques de replay

        data = request.get_json()
        logging.debug("DEBUG: Datos recibidos en webhook: %s", data)
        # ✨ ADDITIONS ✨: Sanitizar datos recibidos
        payment_status = sanitize_input(data.get("status", ""))
        order_id = sanitize_input(data.get("external_reference", ""))
        transaction_id = sanitize_input(data.get("id", ""))
        logging.debug("DEBUG: Webhook data sanitized: order_id: %s, payment_status: %s, transaction_id: %s", order_id, payment_status, transaction_id)

        if order_id and payment_status:
            if payment_status == "approved":
                new_status = "Completado"
            elif payment_status == "rejected":
                new_status = "Rechazado"
            elif payment_status == "pending":
                new_status = "Pendiente"
            else:
                new_status = "Pendiente"

            data_update = {
                "estado_pago": new_status,
                "fecha_actualizacion": "now()"
            }
            if transaction_id:
                data_update["transaction_id"] = transaction_id

            logging.debug("DEBUG: Actualizando orden %s con datos: %s", order_id, data_update)
            response = supabase.table("orders").update(data_update).eq("id", order_id).execute()
            if response.error:
                logging.error("DEBUG: Error actualizando la orden: %s", response.error)
                return "Error actualizando la orden", 500
            logging.debug("DEBUG: Orden %s actualizada a %s", order_id, new_status)
            return "OK", 200
        else:
            logging.debug("DEBUG: Datos insuficientes en webhook")
            return "Datos insuficientes", 400
    except Exception as e:
        logging.exception("DEBUG: Error en el webhook:")
        return "Error en el webhook", 500
