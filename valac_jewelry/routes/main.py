# valac_jewelry/routes/main.py

from flask import Blueprint, render_template, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    supabase = current_app.supabase
    # Se obtiene únicamente los primeros 3 productos
    response = supabase.table("products").select("*").limit(3).execute()
    products = response.data if response.data else []
    return render_template('home.html', products=products)
    return render_template('home.html')

@main_bp.route('/collection')
def collection():
    return render_template('collection.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')
