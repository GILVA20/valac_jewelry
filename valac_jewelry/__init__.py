import os
import logging
import mimetypes
from flask import Flask, request, redirect
from flask_admin import Admin
from supabase import create_client
from dotenv import load_dotenv
from flask_login import LoginManager

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)
logging.basicConfig(level=logging.DEBUG)

def create_app():
    # Ensure .mjs files are served with the correct MIME type.
    # Registering here guarantees it runs before Flask serves static files.
    mimetypes.add_type("application/javascript", ".mjs")

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
    
    # Solo loguear config no-sensible para diagnóstico
    app.logger.debug("FLASK_ENV: %s", os.getenv("FLASK_ENV"))
    app.logger.debug("SIMULAR_PAGO: %s", app.config.get("SIMULAR_PAGO"))
    
    supabase_url = app.config.get("SUPABASE_URL")
    supabase_key = app.config.get("SUPABASE_KEY")
    app.supabase = create_client(supabase_url, supabase_key)
    
    @app.context_processor
    def inject_supabase_storage_url():
        return dict(
            SUPABASE_STORAGE_URL=app.config.get("SUPABASE_STORAGE_URL"),
            CDN_BASE_URL=app.config.get("CDN_BASE_URL"),
            META_PIXEL_ID=app.config.get("META_PIXEL_ID"),  # META PIXEL
        )

    @app.context_processor
    def inject_promo_settings():
        """Load promo banner/section settings for all templates."""
        import json as _json
        try:
            resp = app.supabase.table("site_settings").select("key, value").like("key", "promo_%").execute()
            promo = {r["key"]: r["value"] for r in (resp.data or [])}
        except Exception:
            promo = {}
        # Banner messages
        promo_msgs = None
        if promo.get("promo_banner_active") == "true":
            try:
                promo_msgs = _json.loads(promo.get("promo_banner_messages", "[]"))
            except (_json.JSONDecodeError, TypeError):
                promo_msgs = None
        return dict(promo=promo, promo_msgs=promo_msgs)
    
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


    # Mock checkout (SIEMPRE registrado, como pediste)
    from .routes.mock_checkout import mock_checkout_bp
    app.register_blueprint(mock_checkout_bp)
    from .routes.coupons_api import coupons_api
    app.register_blueprint(coupons_api)
    
    
    admin = Admin(app, name='VALAC Joyas Admin', template_mode='bootstrap3', url='/admin', endpoint='admin')
    from .routes.admin import SupabaseProductAdmin, BulkUploadAdminView, SalesAdmin, PaymentsAdmin, ReportsAdmin
    from .routes.admin_coupons import CouponsAdminView
    from .routes.admin_orders import OrderAdminView
    from .routes.admin_reviews import ReviewsAdminView
    from .routes.admin_promo import PromoAdminView
    from .routes.analytics import AnalyticsAdmin
    admin.add_view(SupabaseProductAdmin(name='Productos Supabase', endpoint='supabase_products'))
    admin.add_view(BulkUploadAdminView(name='Carga Masiva', endpoint='bulk_upload'))
    # Mantén el endpoint "admin_orders" para la vista de órdenes
    admin.add_view(OrderAdminView(name='Órdenes', endpoint='admin_orders'))
    admin.add_view(SalesAdmin(name='Ventas', endpoint='sales'))
    admin.add_view(PaymentsAdmin(name='Pagos / Cobranza', endpoint='payments'))
    admin.add_view(ReportsAdmin(name='Reportes', endpoint='reports'))
    admin.add_view(AnalyticsAdmin(name='Analytics', endpoint='analytics'))
    admin.add_view(CouponsAdminView(name='Cupones', endpoint='admin_coupons'))
    admin.add_view(ReviewsAdminView(name='Reseñas', endpoint='admin_reviews'))
    admin.add_view(PromoAdminView(name='Promociones', endpoint='admin_promo'))

    # Reseñas de clientes (API + página /reseñas)
    from .routes.reviews import reviews_bp
    app.register_blueprint(reviews_bp)

    # VALAC Studio – AI photography
    from .routes.studio import studio_bp
    app.register_blueprint(studio_bp)

    # Anillos de Compromiso – SPA
    from .routes.anillos_compromiso import anillos_bp
    app.register_blueprint(anillos_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
