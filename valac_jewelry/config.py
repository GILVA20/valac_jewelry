import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_URL = os.environ.get('SUPABASE_STORAGE_URL')
    MP_MAX_INSTALLMENTS = os.environ.get('MP_MAX_INSTALLMENTS')
    SIMULAR_PAGO = os.environ.get('SIMULAR_PAGO', 'False').lower() == 'true'
    # ✨ ADDITIONS ✨
    ENV = os.getenv("FLASK_ENV", "development").lower()  # Configuración del ambiente
    IS_PROD = ENV == "production"  # Bandera para producción
    # Se sobreescriben las claves de MercadoPago según el ambiente
    MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN" if IS_PROD else "MP_ACCESS_TOKEN_TEST")
    MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY" if IS_PROD else "MP_PUBLIC_KEY_TEST")
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_SENDER = os.getenv('MAIL_SENDER')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # ========================================================================
    # SALES ASSISTANT CONFIGURATION (Sprint 1 - Infraestructura)
    # ========================================================================
    SALES_ASSISTANT = {
        'whatsapp_number': '+52 771 857 4647',
        'whatsapp_number_clean': '527718574647',  # Sin espacios ni símbolos
        'default_message': 'Hola VALAC, tengo una pregunta',
        'locale': 'es-MX',  # Español de México
        'routes': {
            '/': {
                'title': 'Asesoría VALAC 💎',
                'emoji': '👋',
                'message': 'Hola, estoy visitando su tienda y me gustaría recibir asesoría personalizada.'
            },
            '/collection': {
                'title': 'Asesoría en Colecciones ✨',
                'emoji': '💍',
                'message': 'Hola, estoy viendo sus colecciones de joyería y tengo una duda.'
            }
        }
    }


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
