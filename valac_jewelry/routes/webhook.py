import hmac
import hashlib
import logging
import os
from flask import Blueprint, request, jsonify, current_app
import mercadopago

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')
log = logging.getLogger("valac_jewelry.webhook")

@webhook_bp.route('/mercadopago', methods=['POST'])
def mercadopago_webhook():
    """
    Webhook alternativo de Mercado Pago.
    Consulta la API de MP para verificar el estado real del pago.
    """
    try:
        data = request.get_json() or {}
        log.info("Webhook MP (ruta /webhook): type=%s", data.get('type'))
        
        # Solo procesar notificaciones de pago
        if data.get('type') != 'payment':
            return jsonify({'status': 'ignored'}), 200
        
        payment_id = data.get('data', {}).get('id')
        if not payment_id:
            return jsonify({'status': 'no_payment_id'}), 200
        
        # Consultar API de MP para obtener datos reales
        token = current_app.config.get('MP_ACCESS_TOKEN') or os.getenv('MP_ACCESS_TOKEN')
        if not token:
            log.error("MP_ACCESS_TOKEN no configurado")
            return jsonify({'status': 'config_error'}), 200
        
        mp_sdk = mercadopago.SDK(token)
        payment_response = mp_sdk.payment().get(payment_id)
        
        if payment_response.get('status') != 200:
            log.error("Error consultando pago %s", payment_id)
            return jsonify({'status': 'mp_error'}), 200
        
        payment_data = payment_response.get('response', {})
        order_id = payment_data.get('external_reference')
        payment_status = payment_data.get('status', '')
        
        if not order_id:
            log.warning("Pago sin external_reference: %s", payment_id)
            return jsonify({'status': 'no_order'}), 200
        
        # Mapear estado
        status_map = {
            'approved': 'Completado',
            'authorized': 'Completado',
            'pending': 'Pendiente',
            'in_process': 'Pendiente',
            'rejected': 'Rechazado',
            'cancelled': 'Cancelado'
        }
        new_status = status_map.get(payment_status, 'Pendiente')
        
        # Actualizar en BD
        supabase = current_app.supabase
        response = supabase.table("orders").update({
            "estado_pago": new_status,
            "transaction_id": str(payment_id)
        }).eq("id", order_id).execute()
        
        log.info("Orden %s actualizada a '%s'", order_id, new_status)
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        # Log interno, no exponer detalles
        log.exception("Error en webhook MP")
        return jsonify({'status': 'error_logged'}), 200
