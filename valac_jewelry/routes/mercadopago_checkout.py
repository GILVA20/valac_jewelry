from flask import Blueprint, request, jsonify
import mercadopago
import os

# Configuración de Mercado Pago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
# Inicializamos el SDK de Mercado Pago con el access token configurado
mp = mercadopago.SDK(MP_ACCESS_TOKEN)

# Es importante que el nombre del blueprint coincida con el que luego importas en __init__.py.
mp_checkout_bp = Blueprint('mp_checkout', __name__)

@mp_checkout_bp.route('/create_preference', methods=['POST'])
def create_preference():
    """
    Endpoint para crear una preferencia de pago.
    Se espera recibir en el body un JSON con la llave "items",
    que es una lista de objetos con: title, unit_price y quantity.
    """
    try:
        data = request.get_json()
        if not data or "items" not in data:
            return jsonify({"error": "No se proporcionaron items"}), 400

        items = data["items"]

        preference_data = {
            "items": items,
            "back_urls": {
                "success": "https://valacjoyas.com/success/{order.id}",
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
    """
    Endpoint para recibir notificaciones (webhook) de Mercado Pago.
    Se espera que el cuerpo de la notificación contenga información del pago.
    Aquí se debe validar la notificación (firma, etc.) y actualizar el estado del
    pago en la base de datos según la respuesta.
    """
    try:
        data = request.get_json()
        if data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
            payment_response = mp.payment().get(payment_id)
            payment = payment_response["response"]
            # Aquí actualizas el estado del pago en tu base de datos
            # Ejemplo: si payment["status"] es "approved", marcar el pedido como pagado.
            print(f"Pago {payment_id} recibido con estado: {payment.get('status')}")
        return "", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
