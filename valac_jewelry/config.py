import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_STORAGE_URL = os.environ.get('SUPABASE_STORAGE_URL')
    MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN')
    MP_PUBLIC_KEY = os.environ.get('MP_PUBLIC_KEY')
    MP_MAX_INSTALLMENTS = os.environ.get('MP_MAX_INSTALLMENTS')
    SIMULAR_PAGO = os.environ.get('SIMULAR_PAGO', 'False').lower() == 'true'

class DevelopmentConfig(Config):
    DEBUG = True
    MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN_TEST')
    MP_PUBLIC_KEY = os.environ.get('MP_PUBLIC_KEY_TEST')
class ProductionConfig(Config):
    DEBUG = False
