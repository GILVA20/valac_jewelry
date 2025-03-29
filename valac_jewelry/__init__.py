import os
import logging
from flask import Flask, request, redirect
from flask_admin import Admin
from supabase import create_client
from dotenv import load_dotenv
from flask_login import LoginManager

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)
print(f"DEBUG:valac_jewelry:FLASK_ENV: {os.getenv('FLASK_ENV')}") #para verificar el valor cargado.
logging.basicConfig(level=logging.DEBUG)

def create_app():
    # Calcula la ruta base y define la carpeta estática
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'static')

    # Crea la aplicación con la carpeta estática y configuración relativa a la instancia
    app = Flask(__name__, static_folder=static_folder, instance_relative_config=True)
    
    # Redirigir HTTP a HTTPS y 'valacjoyas.com' a 'www.valacjoyas.com'
    @app.before_request
    def enforce_https_and_www():
        if request.headers.get('X-Forwarded-Proto') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
        if request.host == 'valacjoyas.com':
            url = request.url.replace('valacjoyas.com', 'www.valacjoyas.com', 1)
            return redirect(url, code=301)
    
    # Cargar la configuración basada en el entorno
    from .config import ProductionConfig, DevelopmentConfig
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        app.config.from_object(ProductionConfig)
        logging.debug("Cargando configuración de producción")
    else:
        app.config.from_object(DevelopmentConfig)
        logging.debug("Cargando configuración de desarrollo")
    
    # Registrar todas las variables de entorno en el logger
    for key, value in os.environ.items():
        app.logger.debug(f"{key} = {value}")
    
    # Debug: imprimir credenciales de MercadoPago y el valor de SIMULAR_PAGO
    app.logger.debug("FLASK_ENV: %s", os.getenv("FLASK_ENV"))
    app.logger.debug("SIMULAR_PAGO: %s", app.config.get("SIMULAR_PAGO"))
    app.logger.debug("MP_ACCESS_TOKEN: %s", app.config.get("MP_ACCESS_TOKEN"))
    app.logger.debug("MP_PUBLIC_KEY: %s", app.config.get("MP_PUBLIC_KEY"))
    
    # Inicializa el cliente de Supabase y lo asigna a la app
    supabase_url = app.config.get("SUPABASE_URL")
    supabase_key = app.config.get("SUPABASE_KEY")
    app.supabase = create_client(supabase_url, supabase_key)

    # Inyecta la variable SUPABASE_STORAGE_URL en todas las plantillas
    @app.context_processor
    def inject_supabase_storage_url():
        return dict(SUPABASE_STORAGE_URL=app.config.get("SUPABASE_STORAGE_URL"))
    
    # Inicializar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    @login_manager.user_loader
    def load_user(user_id):
        from .auth import AdminUser
        if user_id == "1":
            return AdminUser(1, os.getenv("ADMIN_USERNAME"))
        return None

    # Registrar blueprint de autenticación
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    # Registrar blueprints de la aplicación
    from .routes.main import main_bp
    app.register_blueprint(main_bp)
    
    from .routes.collection import collection_bp
    app.register_blueprint(collection_bp, url_prefix='/collection')
    
    from .routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix='/producto')
    
    from .routes.cart import cart_bp
    app.register_blueprint(cart_bp, url_prefix='/cart')

    from .routes.success import success_bp
    app.register_blueprint(success_bp)

    from .routes.failure import failure_bp
    app.register_blueprint(failure_bp)

    from .routes.pending import pending_bp
    app.register_blueprint(pending_bp)

    from .routes.contact import contact_bp
    app.register_blueprint(contact_bp)
    
    from .routes.checkout import checkout_bp
    app.register_blueprint(checkout_bp)
    
    # Registrar el blueprint de MercadoPago Checkout
    from .routes.mercadopago_checkout import mp_checkout_bp
    app.register_blueprint(mp_checkout_bp)
    
    # Inicializa Flask-Admin con la vista personalizada para Supabase
    admin = Admin(app, name='VALAC Joyas Admin', template_mode='bootstrap3', url='/admin', endpoint='admin')
    from .routes.admin import SupabaseProductAdmin
    admin.add_view(SupabaseProductAdmin(name='Productos Supabase', endpoint='supabase_products'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
