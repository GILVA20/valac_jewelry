# valac_jewelry/__init__.py
from flask import Flask
from .config import Config
from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, db
from firebase_admin import credentials, initialize_app
import os
    # Importar y registrar los Blueprints
from .routes.main import main_bp
from .routes.collection import collections_bp
from .routes.products import products_bp

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Inicializar Firebase (si lo necesitas aquí, o en otro módulo de configuración)
    # 1. Inicializar Firebase
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(base_dir, 'instance', 'valacjoyas-e23f2-firebase-adminsdk-fbsvc-f4e24e9ab4.json')
    
        # Calcular la ruta base (la carpeta raíz de tu proyecto)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Construir la ruta absoluta a la carpeta "static"
    static_folder = os.path.join(base_dir, 'static') 
        # Crear la aplicación usando la ruta absoluta para la carpeta estática
    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(Config)

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://valacjoyas-e23f2-default-rtdb.firebaseio.com/'
    })


    app.register_blueprint(main_bp)  # Rutas sin prefijo, p.ej: '/', '/about'
    app.register_blueprint(collections_bp, url_prefix='/collection')
    app.register_blueprint(products_bp, url_prefix='/producto')

    return app
