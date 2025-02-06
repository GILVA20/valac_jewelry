# valac_jewelry/routes/products.py
from flask import Blueprint, render_template, current_app

products_bp = Blueprint('products', __name__)

@products_bp.route('/<int:product_id>')
def detail(product_id):
    supabase = current_app.supabase
    response = supabase.table("products").select("*").eq("id", product_id).execute()
    product = response.data[0] if response.data and len(response.data) > 0 else None
    return render_template('product_detail.html', product=product)
