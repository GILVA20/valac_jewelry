"""
routes/test.py - Rutas de testing
"""
from flask import Blueprint, render_template

test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/whatsapp')
def test_whatsapp():
    """Página de test para WhatsApp button"""
    return render_template('test_whatsapp.html')

@test_bp.route('/debug')
def debug():
    """Información de debug"""
    from flask import current_app
    return {
        'status': 'OK',
        'sales_assistant_config': current_app.config.get('SALES_ASSISTANT', {}),
        'whatsapp_number': current_app.config.get('SALES_ASSISTANT', {}).get('whatsapp_number'),
        'message': 'Abre http://localhost:5000/test/whatsapp para probar el botón'
    }
