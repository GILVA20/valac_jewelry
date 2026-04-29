import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_URL = os.environ.get('SUPABASE_STORAGE_URL')
    CDN_BASE_URL = os.environ.get('CDN_BASE_URL') or os.environ.get('SUPABASE_STORAGE_URL')
    MP_MAX_INSTALLMENTS = os.environ.get('MP_MAX_INSTALLMENTS')
    SIMULAR_PAGO = os.environ.get('SIMULAR_PAGO', 'False').lower() == 'true'
    # ✨ ADDITIONS ✨
    ENV = os.getenv("FLASK_ENV", "development").lower()  # Configuración del ambiente
    IS_PROD = ENV == "production"  # Bandera para producción
    
    # Claves de MercadoPago - PRODUCCIÓN
    MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
    MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY")
    
    # Claves de MercadoPago - TEST (siempre cargarlas para poder usarlas en localhost)
    MP_ACCESS_TOKEN_TEST = os.getenv("MP_ACCESS_TOKEN_TEST")
    MP_PUBLIC_KEY_TEST = os.getenv("MP_PUBLIC_KEY_TEST")
    
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_SENDER = os.getenv('MAIL_SENDER')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # WhatsApp Business - Número de VALAC Joyas
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '527718574647')

    # META PIXEL — ID del píxel de Meta (Facebook)
    META_PIXEL_ID = os.environ.get('META_PIXEL_ID')

    # VALAC Studio – AI photography
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GOOGLE_GENAI_API_KEY = os.environ.get('GOOGLE_GENAI_API_KEY')
    CLAUDE_MODEL = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
    GEMINI_IMAGEN_MODEL = os.environ.get('GEMINI_IMAGEN_MODEL', 'imagen-4.0-fast-generate-001')
    GEMINI_FLASH_MODEL = os.environ.get('GEMINI_FLASH_MODEL', 'gemini-2.5-flash-image')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
