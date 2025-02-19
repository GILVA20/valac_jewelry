## valac_jewelry/routes/products.py
#from flask import Blueprint, render_template, current_app
#
#products_bp = Blueprint('products', __name__)
#
#@products_bp.route('/<int:product_id>')
#def detail(product_id):
#    supabase = current_app.supabase
#    response = supabase.table("products").select("*").eq("id", product_id).execute()
#    product = response.data[0] if response.data and len(response.data) > 0 else None
#    return render_template('product_detail.html', product=product)
#
# valac_jewelry/routes/products.py
from flask import Blueprint, render_template, request, current_app, abort

products_bp = Blueprint('products', __name__, url_prefix='/product')

@products_bp.route('/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    """
    Muestra la página de detalle de un producto específico.
    """
    supabase = current_app.supabase
    response = supabase.table('products').select('*').eq('id', product_id).single().execute()
    if response.error or not response.data:
        abort(404, description="Producto no encontrado")
    
    product = response.data
    
    # Podríamos cargar productos relacionados (ej. misma categoría)
    # para mostrarlos en "También te puede interesar".
    related_resp = supabase.table('products') \
                    .select('*') \
                    .eq('tipo_producto', product['tipo_producto']) \
                    .neq('id', product_id) \
                    .limit(4) \
                    .execute()
    related_products = related_resp.data if related_resp.data else []
    
    return render_template('product.html', product=product, related_products=related_products)
