import os
import logging
from flask import Flask
from flask_admin import Admin
from supabase import create_client
from .config import Config

logging.basicConfig(level=logging.DEBUG)

def create_app():
    # Calcula la ruta base y define la carpeta estática
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'static')
    
    # Crea la aplicación
    app = Flask(__name__, static_folder=static_folder, instance_relative_config=True)
    app.config.from_object(Config)
    
    # Inicializa el cliente de Supabase y lo asigna a la app
    supabase_url = app.config.get("SUPABASE_URL")
    supabase_key = app.config.get("SUPABASE_KEY")
    app.supabase = create_client(supabase_url, supabase_key)
    
    # Registrar blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)
    
    from .routes.collection import collection_bp  # Asegúrate de que en collection.py el blueprint se llame collection_bp
    app.register_blueprint(collection_bp, url_prefix='/collection')
    
    from .routes.products import products_bp
    app.register_blueprint(products_bp, url_prefix='/producto')
    
    from .routes.cart import cart_bp  # Blueprint para el carrito
    app.register_blueprint(cart_bp, url_prefix='/cart')
    
    # Registrar blueprint de checkout
    from .routes.checkout import checkout_bp
    app.register_blueprint(checkout_bp)  # Opcional: puedes agregar url_prefix='/checkout' si lo deseas
    
    # Inicializa Flask-Admin con la vista personalizada para Supabase
    admin = Admin(app, name='VALAC Joyas Admin', template_mode='bootstrap3', url='/admin', endpoint='admin')
    from .routes.admin import SupabaseProductAdmin
    admin.add_view(SupabaseProductAdmin(name='Productos Supabase', endpoint='supabase_products'))
    
    return app
