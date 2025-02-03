# valac_jewelry/routes/products.py
from flask import Blueprint, render_template
from firebase_admin import db

products_bp = Blueprint('products', __name__)

@products_bp.route('/<producto_id>')
def producto_detalle(producto_id):
    ref = db.reference(f'catalogo/{producto_id}')
    producto = ref.get()
    if producto:
        return render_template('producto_detalle.html', producto=producto)
    else:
        return render_template('404.html'), 404
