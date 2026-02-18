import os
import logging
from flask import Blueprint, request, jsonify, current_app, flash, redirect, url_for
import mercadopago
from supabase import create_client, Client  # Asegúrate de tener instalado supabase-py

# ✨ ADDITIONS ✨
ENV = os.getenv("FLASK_ENV", "development").lower()
IS_PROD = ENV == "production"
logging.debug("DEBUG: In mercadopago_checkout: ENV=%s, IS_PROD=%s", ENV, IS_PROD)

def sanitize_input(input_str):
    return str(input_str).strip().replace("<", "&lt;").replace(">", "&gt;")

# Configuración de MercadoPago según entorno
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN" if IS_PROD else "MP_ACCESS_TOKEN_TEST")
MP_PUBLIC_KEY    = os.getenv("MP_PUBLIC_KEY" if IS_PROD else "MP_PUBLIC_KEY_TEST")
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
    Crea una preferencia de Mercado Pago.
    Espera un JSON con:
      - items: lista de {title, unit_price, quantity}
      - order_id: tu ID interno para external_reference
    """
    try:
        data = request.get_json()
        logging.debug("DEBUG: Datos recibidos en create_preference: %s", data)

        # Validar order_id para external_reference
        order_id = data.get("order_id")
        if not order_id:
            logging.debug("DEBUG: order_id no proporcionado para external_reference")
            return jsonify({"error": "order_id es obligatorio para external_reference"}), 400

        # Sanitizar items
        if "items" in data:
            sanitized_items = []
            for item in data["items"]:
                sanitized_item = {
                    k: sanitize_input(v) if isinstance(v, str) else v
                    for k, v in item.items()
                }
                sanitized_items.append(sanitized_item)
            data["items"] = sanitized_items
            logging.debug("DEBUG: Items sanitizados: %s", data["items"])

        if not data or "items" not in data:
            logging.debug("DEBUG: No se proporcionaron items en la solicitud")
            return jsonify({"error": "No se proporcionaron items"}), 400

        items = data["items"]
        logging.debug("DEBUG: Items recibidos: %s", items)

        # Construir preference_data con external_reference
        preference_data = {
            "items": items,
            "back_urls": {
                "success": "https://valacjoyas.com/success",
                "failure": "https://valacjoyas.com/failure",
                "pending": "https://valacjoyas.com/pending"
            },
            "notification_url": "https://valacjoyas.com/webhook",
            "payment_methods": {
                "installments": 12
            },
            "external_reference": order_id
            }
        logging.debug("DEBUG: Datos de preferencia a crear: %s", preference_data)

        # Reinstanciar SDK con token del app.config
        token = current_app.config["MP_ACCESS_TOKEN"]
        logging.debug("DEBUG: Token seleccionado: %s", token)
        mp = mercadopago.SDK(token)

        # Marcar ambiente de prueba
        if not IS_PROD:
            preference_data.setdefault("metadata", {}).update({"environment": "test"})
            logging.debug("DEBUG: Preference data updated for test environment: %s", preference_data)

        preference_response = mp.preference().create(preference_data)
        logging.debug("DEBUG: Respuesta de la creación de preferencia: %s", preference_response)
        if not preference_response or "response" not in preference_response:
            logging.error("DEBUG: Respuesta inválida de MercadoPago: %s", preference_response)
            flash("Error en la respuesta de MercadoPago, por favor inténtalo nuevamente.", "error")
            return redirect(url_for('checkout.checkout'))

        preference = preference_response["response"]
        logging.debug("DEBUG: Preferencia creada: %s", preference)
        return jsonify({"id": preference["id"]}), 200

    except Exception as e:
        logging.exception("Error al crear preferencia de MercadoPago")
        # NO exponer el error interno al usuario
        return jsonify({"error": "Error al procesar el pago. Por favor, inténtalo de nuevo."}), 500


@mp_checkout_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook de Mercado Pago - Procesa notificaciones de pago.
    IMPORTANTE: Consulta la API de MP para confirmar el estado real del pago.
    """
    try:
        data = request.get_json() or {}
        logging.info("Webhook MP recibido: type=%s, action=%s", data.get('type'), data.get('action'))
        
        # MP envía diferentes tipos de notificaciones
        notification_type = data.get('type')
        
        # Solo procesamos notificaciones de pago
        if notification_type == 'payment':
            payment_id = data.get('data', {}).get('id')
            
            if not payment_id:
                logging.warning("Webhook sin payment_id")
                return jsonify({"status": "ignored", "reason": "no payment_id"}), 200
            
            # CRÍTICO: Consultar la API de MP para obtener datos REALES del pago
            # No confiar solo en los datos del webhook
            token = current_app.config.get("MP_ACCESS_TOKEN") or os.getenv("MP_ACCESS_TOKEN")
            mp_sdk = mercadopago.SDK(token)
            
            payment_response = mp_sdk.payment().get(payment_id)
            
            if payment_response.get('status') != 200:
                logging.error("Error consultando pago %s en MP: %s", payment_id, payment_response)
                return jsonify({"status": "error", "reason": "mp_api_error"}), 200
            
            payment_data = payment_response.get('response', {})
            
            # Obtener external_reference (nuestro order_id)
            ext_ref = payment_data.get('external_reference')
            if not ext_ref:
                logging.warning("Pago %s sin external_reference", payment_id)
                return jsonify({"status": "ignored", "reason": "no external_reference"}), 200
            
            payment_status = payment_data.get('status', '')
            transaction_id = str(payment_id)
            
            logging.info("Procesando pago: order_id=%s, status=%s, payment_id=%s", 
                        ext_ref, payment_status, payment_id)
            
            # Mapear estado de MP a estado interno
            status_mapping = {
                "approved": "Completado",
                "authorized": "Completado",
                "pending": "Pendiente",
                "in_process": "Pendiente",
                "rejected": "Rechazado",
                "cancelled": "Cancelado",
                "refunded": "Reembolsado",
                "charged_back": "Contracargo"
            }
            new_status = status_mapping.get(payment_status, "Pendiente")
            
            # Actualizar orden en Supabase
            data_update = {
                "estado_pago": new_status,
                "transaction_id": transaction_id
            }
            
            response = supabase.table("orders").update(data_update).eq("id", ext_ref).execute()
            
            if not response.data:
                logging.error("No se encontró orden %s para actualizar", ext_ref)
            else:
                logging.info("Orden %s actualizada a '%s' (payment_id=%s)", ext_ref, new_status, payment_id)
            
        # Siempre responder 200 para que MP no reintente
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        # Log del error pero NO exponerlo
        logging.exception("Error procesando webhook de MP")
        # Responder 200 para evitar reintentos infinitos de MP
        return jsonify({"status": "error_logged"}), 200
