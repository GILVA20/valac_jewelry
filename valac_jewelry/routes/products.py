from flask import Blueprint, render_template, abort, current_app

products_bp = Blueprint('products', __name__, url_prefix='/product')

@products_bp.route('/<int:product_id>', methods=['GET'])
def product_detail(product_id):
    """
    Muestra la página de detalle de un producto específico.
    """
    supabase = current_app.supabase
    # Ejecutamos la query y obtenemos la respuesta
    response = supabase.table('products').select('*').eq('id', product_id).single().execute()
    
    # Solo comprobamos si hay datos; eliminamos la comprobación de "response.error"
    if not response.data:
        abort(404, description="Producto no encontrado")
    
    product = response.data

    # Consultamos productos relacionados (misma categoría, excluyendo el actual)
    related_resp = supabase.table('products')\
                    .select('*')\
                    .eq('tipo_producto', product['tipo_producto'])\
                    .neq('id', product_id)\
                    .limit(4)\
                    .execute()
    related_products = related_resp.data if related_resp.data else []
    
    return render_template('product.html', product=product, related_products=related_products)
