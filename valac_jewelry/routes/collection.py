# valac_jewelry/routes/collection.py
from flask import Blueprint, render_template, current_app

collections_bp = Blueprint('collection', __name__)

@collections_bp.route('/')
def collection_home():
    supabase = current_app.supabase
    response = supabase.table("products").select("*").execute()
    # Si response.data existe, úsalo; de lo contrario, asigna una lista vacía
    products = response.data if response.data else []
    return render_template('collection.html', products=products)

@collections_bp.route('/')
def list_products():
    supabase = current_app.supabase
    response = supabase.table("products").select("*").execute()
    if not response.data:
        current_app.logger.error("Error al obtener productos: " + str(response))
        products = []
    else:
        products = response.data
        current_app.logger.info(f"Productos obtenidos: {products}")
    return render_template('collection.html', products=products)
