from flask import Blueprint, render_template, abort, current_app

products_bp = Blueprint('products', __name__, url_prefix='/product')

@products_bp.route('/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    """
    Muestra la página de detalle de un producto específico.
    """
    supabase = current_app.supabase
    _PUBLIC_FIELDS = (
        "id, nombre, descripcion, precio, descuento_pct, precio_descuento, "
        "tipo_producto, genero, tipo_oro, imagen, stock_total, destacado, created_at"
    )
    response = supabase.table('products').select(_PUBLIC_FIELDS).eq('id', product_id).single().execute()
    
    if not response.data:
        abort(404, description="Producto no encontrado")

    product = response.data
    if not product.get("activo", True):
        abort(404, description="Producto no encontrado")

    # 🔄 MVP 1: Cargar imágenes múltiples del producto desde product_images
    images_resp = supabase.table('product_images')\
        .select('*')\
        .eq('product_id', product_id)\
        .order('orden')\
        .execute()
    product['images'] = images_resp.data or []

    related_resp = supabase.table('products')\
                    .select('id, nombre, precio, descuento_pct, precio_descuento, tipo_producto, imagen, product_images(imagen,orden)')\
                    .eq('tipo_producto', product['tipo_producto'])\
                    .eq('activo', True)\
                    .neq('id', product_id)\
                    .limit(4)\
                    .execute()
    related_products = related_resp.data if related_resp.data else []
    
    return render_template('product.html', product=product, related_products=related_products)
