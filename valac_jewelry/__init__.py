import os
import logging
from flask import Flask
from flask_admin import Admin
from supabase import create_client
from dotenv import load_dotenv
from flask_login import LoginManager

# Cargar variables de entorno desde el archivo .env
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

def create_app():
    # Calcula la ruta base y define la carpeta estática
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'static')

    # Crea la aplicación con la carpeta estática y configuración relativa a la instancia
    app = Flask(__name__, static_folder=static_folder, instance_relative_config=True)
    
    # Cargar la configuración basada en el entorno
    from .config import ProductionConfig, DevelopmentConfig
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        app.config.from_object(ProductionConfig)
        logging.debug("Cargando configuración de producción")
    else:
        app.config.from_object(DevelopmentConfig)
        logging.debug("Cargando configuración de desarrollo")
    
    print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
    print("FLASK_ENV:", os.getenv("FLASK_ENV"))

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
    login_manager.login_view = 'auth.login'  # Esta vista se definirá en el blueprint de autenticación

    @login_manager.user_loader
    def load_user(user_id):
        # Para este ejemplo, asumimos que solo hay un usuario administrador.
        # Importamos la clase AdminUser definida en auth.py
        from .auth import AdminUser
        # Si el user_id es "1", retornamos el AdminUser utilizando el nombre del entorno.
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
    
    from .routes.contact import contact_bp
    app.register_blueprint(contact_bp)
    
    from .routes.checkout import checkout_bp
    app.register_blueprint(checkout_bp)
    
    # Inicializa Flask-Admin con la vista personalizada para Supabase
    admin = Admin(app, name='VALAC Joyas Admin', template_mode='bootstrap3', url='/admin', endpoint='admin')
    from .routes.admin import SupabaseProductAdmin
    admin.add_view(SupabaseProductAdmin(name='Productos Supabase', endpoint='supabase_products'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Nota: para producción usar Gunicorn u otro servidor WSGI
    app.run(debug=True)
