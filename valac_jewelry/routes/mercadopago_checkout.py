import os
from flask import Blueprint, request, jsonify
import mercadopago
from supabase import create_client, Client  # Asegúrate de tener instalado supabase-py

# Configuración de MercadoPago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# Configuración Supabase (las variables SUPABASE_URL y SUPABASE_KEY deben estar definidas)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
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
        if not data or "items" not in data:
            return jsonify({"error": "No se proporcionaron items"}), 400

        items = data["items"]

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

        preference_response = mp.preference().create(preference_data)
        preference = preference_response["response"]
        return jsonify({"id": preference["id"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@mp_checkout_bp.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    payment_status = data.get("status")
    order_id = data.get("external_reference")  # Debe coincidir con lo enviado en external_reference
    transaction_id = data.get("id")  # Id de la transacción de MercadoPago

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

        response = supabase.table("orders").update(data_update).eq("id", order_id).execute()
        if response.error:
            print("Error actualizando la orden:", response.error)
            return "Error actualizando la orden", 500
        print(f"Orden {order_id} actualizada a {new_status}")
        return "OK", 200
    else:
        return "Datos insuficientes", 400
