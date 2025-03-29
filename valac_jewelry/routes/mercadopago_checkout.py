import os
import logging
from flask import Blueprint, request, jsonify
import mercadopago
from supabase import create_client, Client  # Asegúrate de tener instalado supabase-py

# Configuración de MercadoPago: se selecciona el token según el entorno
MP_ACCESS_TOKEN = os.getenv("FLASK_ENV", "development").lower() == "production" and os.getenv("MP_ACCESS_TOKEN") or os.getenv("MP_ACCESS_TOKEN_TEST")
logging.debug("MP_ACCESS_TOKEN utilizado: %s", MP_ACCESS_TOKEN)
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
logging.debug("SUPABASE_URL: %s", SUPABASE_URL)
logging.debug("SUPABASE_KEY: %s", SUPABASE_KEY)
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
        logging.debug("Datos recibidos en create_preference: %s", data)
        if not data or "items" not in data:
            logging.debug("No se proporcionaron items en la solicitud")
            return jsonify({"error": "No se proporcionaron items"}), 400

        items = data["items"]
        logging.debug("Items recibidos: %s", items)

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
        logging.debug("Datos de preferencia a crear: %s", preference_data)

        preference_response = mp.preference().create(preference_data)
        logging.debug("Respuesta de la creación de preferencia: %s", preference_response)
        preference = preference_response["response"]
        logging.debug("Preferencia creada: %s", preference)
        return jsonify({"id": preference["id"]}), 200
    except Exception as e:
        logging.exception("Error al crear preferencia:")
        return jsonify({"error": str(e)}), 500

@mp_checkout_bp.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.debug("Datos recibidos en webhook: %s", data)
        payment_status = data.get("status")
        order_id = data.get("external_reference")  # Debe coincidir con lo enviado en external_reference
        transaction_id = data.get("id")  # Id de la transacción de MercadoPago

        logging.debug("Webhook: order_id: %s, payment_status: %s, transaction_id: %s", order_id, payment_status, transaction_id)

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

            logging.debug("Actualizando orden %s con datos: %s", order_id, data_update)
            response = supabase.table("orders").update(data_update).eq("id", order_id).execute()
            if response.error:
                logging.error("Error actualizando la orden: %s", response.error)
                return "Error actualizando la orden", 500
            logging.debug("Orden %s actualizada a %s", order_id, new_status)
            return "OK", 200
        else:
            logging.debug("Datos insuficientes en webhook")
            return "Datos insuficientes", 400
    except Exception as e:
        logging.exception("Error en el webhook:")
        return "Error en el webhook", 500
