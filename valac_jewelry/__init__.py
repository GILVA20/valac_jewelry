import os
import logging
from flask import Flask, request, redirect
from flask_admin import Admin
from supabase import create_client
from dotenv import load_dotenv
from flask_login import LoginManager

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)
print(f"                DEBUG:valac_jewelry:FLASK_ENV: {os.getenv('FLASK_ENV')}                                           ")
logging.basicConfig(level=logging.DEBUG)

def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'static')
    app = Flask(__name__, static_folder=static_folder, instance_relative_config=True)
    
    @app.before_request
    def enforce_https_and_www():
        if request.headers.get('X-Forwarded-Proto') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
        if request.host == 'valacjoyas.com':
            url = request.url.replace('valacjoyas.com', 'www.valacjoyas.com', 1)
            return redirect(url, code=301)
    
    from .config import ProductionConfig, DevelopmentConfig
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        app.config.from_object(ProductionConfig)
        logging.debug("Cargando configuración de producción")
    else:
        app.config.from_object(DevelopmentConfig)
        logging.debug("Cargando configuración de desarrollo")
    
    for key, value in os.environ.items():
        app.logger.debug(f"{key} = {value}")
    
    app.logger.debug("FLASK_ENV: %s", os.getenv("FLASK_ENV"))
    app.logger.debug("SIMULAR_PAGO: %s", app.config.get("SIMULAR_PAGO"))
    app.logger.debug("MP_ACCESS_TOKEN: %s", app.config.get("MP_ACCESS_TOKEN"))
    app.logger.debug("MP_PUBLIC_KEY: %s", app.config.get("MP_PUBLIC_KEY"))
    
    supabase_url = app.config.get("SUPABASE_URL")
    supabase_key = app.config.get("SUPABASE_KEY")
    app.supabase = create_client(supabase_url, supabase_key)
    
    @app.context_processor
    def inject_supabase_storage_url():
        return dict(SUPABASE_STORAGE_URL=app.config.get("SUPABASE_STORAGE_URL"))
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    @login_manager.user_loader
    def load_user(user_id):
        from .auth import AdminUser
        if user_id == "1":
            return AdminUser(1, os.getenv("ADMIN_USERNAME"))
        return None
    
    from .auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from .routes.main import main_bp
    app.register_blueprint(main_bp)
    
    from .routes.collection import collection_bp
    app.register_blueprint(collection_bp, url_prefix='/collection')
    
    from .routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix='/producto')
    
    from .routes.cart import cart_bp
    app.register_blueprint(cart_bp, url_prefix='/cart')
    from .routes.contact import contact_bp
    app.register_blueprint(contact_bp)

        # Registrar blueprint de órdenes para seguimiento
    from .routes.orders import orders_bp
    app.register_blueprint(orders_bp)
    
    # Registrar rutas de pago
    from .routes.success import success_bp
    app.register_blueprint(success_bp)
    
    from .routes.failure import failure_bp
    app.register_blueprint(failure_bp)
    
    from .routes.pending import pending_bp
    app.register_blueprint(pending_bp)
    
    from .routes.webhook import webhook_bp
    app.register_blueprint(webhook_bp)
    
    from .routes.checkout import checkout_bp
    app.register_blueprint(checkout_bp)
    
    from .routes.mercadopago_checkout import mp_checkout_bp
    app.register_blueprint(mp_checkout_bp)

    from .routes.mock_checkout import mock_checkout_bp
    app.register_blueprint(mock_checkout_bp)
    
    admin = Admin(app, name='VALAC Joyas Admin', template_mode='bootstrap3', url='/admin', endpoint='admin')
    from .routes.admin import SupabaseProductAdmin, BulkUploadAdminView, SalesAdmin, PaymentsAdmin, ReportsAdmin
    from .routes.admin_orders import OrderAdminView
    from .routes.analytics import AnalyticsAdmin
    admin.add_view(SupabaseProductAdmin(name='Productos Supabase', endpoint='supabase_products'))
    admin.add_view(BulkUploadAdminView(name='Carga Masiva', endpoint='bulk_upload'))
    # Mantén el endpoint "admin_orders" para la vista de órdenes
    admin.add_view(OrderAdminView(name='Órdenes', endpoint='admin_orders'))
    admin.add_view(SalesAdmin(name='Ventas', endpoint='sales'))
    admin.add_view(PaymentsAdmin(name='Pagos / Cobranza', endpoint='payments'))
    admin.add_view(ReportsAdmin(name='Reportes', endpoint='reports'))
    admin.add_view(AnalyticsAdmin(name='Analytics', endpoint='analytics'))
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
