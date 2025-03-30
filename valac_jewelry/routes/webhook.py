import hmac, hashlib
from flask import Blueprint, request, jsonify, current_app

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

@webhook_bp.route('/mercadopago', methods=['POST'])
def mercadopago_webhook():
    # Obtener la firma del header (ej. 'X-Hub-Signature')
    signature = request.headers.get('X-Hub-Signature')
    secret = current_app.config.get('MP_WEBHOOK_SECRET')
    payload = request.get_data()

    # Calcular la firma usando HMAC SHA256
    computed_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_signature, signature):
        current_app.logger.error("Firma inválida en el webhook de MercadoPago")
        return jsonify({'error': 'Firma inválida'}), 400

    data = request.get_json()
    order_id = data.get('data', {}).get('id')
    status = data.get('action')  # O data.get('status') según la estructura recibida

    # Mapear estado de MercadoPago a estado interno
    if status == 'approved':
        new_status = 'Completado'
    elif status == 'rejected':
        new_status = 'Fallido'
    else:
        new_status = 'Pendiente'

    supabase = current_app.supabase
    response = supabase.table("orders").update({"estado_pago": new_status}).eq("id", order_id).execute()
    current_app.logger.debug("Webhook: Orden %s actualizada a %s. Respuesta: %s", order_id, new_status, response)
    return jsonify({'message': 'OK'}), 200
