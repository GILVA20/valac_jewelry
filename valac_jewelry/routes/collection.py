# valac_jewelry/routes/collections.py
from flask import Blueprint, render_template
from firebase_admin import db
import logging
collections_bp = Blueprint('collection', __name__)

@collections_bp.route('/<coleccion_slug>')
def collection(coleccion_slug):
    # Consulta a Firebase para obtener los productos de la colección
    ref = db.reference(f'collection/{coleccion_slug}/productos')
    productos = ref.get()  # Se espera un diccionario de productos
    productos_lista = list(productos.values()) if productos else []
    logging.debug("Se ha accedido a la ruta /collections/ del blueprint.")
    return render_template('collection.html', productos=productos_lista, coleccion=coleccion_slug)
