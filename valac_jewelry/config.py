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
    MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN_PROD" if IS_PROD else "MP_ACCESS_TOKEN_TEST")
    MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY_PROD" if IS_PROD else "MP_PUBLIC_KEY_TEST")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
