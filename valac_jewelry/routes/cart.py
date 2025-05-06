from flask import Blueprint, render_template, redirect, url_for, session, current_app, flash, request
from functools import wraps
import logging

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')
logger = logging.getLogger(__name__)

# Función auxiliar para asegurar que el carrito se maneje como diccionario con claves tipo string
def get_cart_data():
    cart_data = session.get('cart', {})
    if not isinstance(cart_data, dict):
        cart_data = {}
    # Aseguramos que las claves sean strings
    cart_data = {str(k): v for k, v in cart_data.items()}
    return cart_data

# Decorador para verificar si el carrito (diccionario) está vacío
def cart_not_empty(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_cart_data():
            flash("Tu carrito está vacío.", 'warning')
            return redirect(url_for('cart.view_cart'))
        return f(*args, **kwargs)
    return decorated_function

@cart_bp.route('/')
def view_cart():
    """
    Muestra los productos en el carrito.
    La sesión almacena el carrito como un diccionario {producto_id (str): cantidad}.
    Se consulta Supabase para obtener la información actual de cada producto.
    """
    supabase = current_app.supabase
    cart_data = get_cart_data()
    if not cart_data:
        flash("No hay productos en el carrito.", 'info')
        return render_template('cart.html', products=[])
    
    products = []
    for product_key, quantity in cart_data.items():
        try:
            # Convertir la clave a entero para la consulta a la base de datos
            product_id = int(product_key)
            resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
            if resp.data:
                # Validar stock si existe (suponiendo que 'stock' es un campo)
                if 'stock' in resp.data and resp.data['stock'] < quantity:
                    flash(f"El producto '{resp.data.get('nombre', 'desconocido')}' no tiene suficiente stock.", 'error')
                else:
                    prod = resp.data
                    prod['cantidad'] = quantity
                    # ✨ Unidad a cobrar: si hay descuento, usamos precio_descuento
                    pct = prod.get('descuento_pct') or 0
                    if pct > 0 and prod.get('precio_descuento') is not None:
                        prod['unit_price'] = prod['precio_descuento']
                    else:
                        prod['unit_price'] = prod['precio']
                    products.append(prod)

            else:
                flash(f"El producto con ID {product_id} no está disponible.", 'error')
        except Exception as e:
            logger.error(f"Error consultando producto {product_key}: {e}")
            flash(f"Error al consultar el producto con ID {product_key}.", 'error')
    return render_template('cart.html', products=products)

@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """
    Agrega un producto al carrito.
    Si ya existe, incrementa la cantidad.
    Verifica la existencia del producto y su stock.
    """
    supabase = current_app.supabase
    try:
        resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
    except Exception as e:
        logger.error(f"Error al consultar producto {product_id}: {e}")
        flash("Error al consultar la disponibilidad del producto.", 'error')
        return redirect(url_for('cart.view_cart'))
    
    if not resp.data:
        flash("El producto no está disponible.", 'error')
        return redirect(url_for('cart.view_cart'))
    
    if 'stock' in resp.data and resp.data['stock'] <= 0:
        flash("El producto está agotado.", 'error')
        return redirect(url_for('cart.view_cart'))
    
    cart_data = get_cart_data()
    key = str(product_id)
    if key in cart_data:
        cart_data[key] += 1
        flash("Cantidad actualizada en el carrito.", 'info')
    else:
        cart_data[key] = 1
        flash("Producto agregado al carrito.", 'success')
    session['cart'] = cart_data
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """
    Elimina un producto del carrito.
    Si la cantidad es mayor a 1, se elimina el producto por completo.
    """
    cart_data = get_cart_data()
    key = str(product_id)
    if key in cart_data:
        del cart_data[key]
        session['cart'] = cart_data
        flash("Producto eliminado del carrito.", 'success')
    else:
        flash("El producto no está en el carrito.", 'error')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    """
    Actualiza la cantidad de un producto en el carrito.
    Si la cantidad es 0 o menor, se elimina el producto.
    """
    try:
        new_qty = int(request.form.get('quantity', 1))
    except ValueError:
        flash("Cantidad inválida.", 'error')
        return redirect(url_for('cart.view_cart'))
    
    cart_data = get_cart_data()
    key = str(product_id)
    if new_qty <= 0:
        if key in cart_data:
            del cart_data[key]
            flash("Producto eliminado del carrito.", 'success')
    else:
        cart_data[key] = new_qty
        flash("Cantidad actualizada.", 'success')
    session['cart'] = cart_data
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/wishlist')
def view_wishlist():
    """
    Muestra los productos de la lista de deseos.
    """
    supabase = current_app.supabase
    wishlist_items = session.get('wishlist', [])
    if not wishlist_items:
        flash("No hay productos en tu lista de deseos.", 'info')
        return render_template('wishlist.html', products=[])
    
    products = []
    for product_id in wishlist_items:
        try:
            resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
            if resp.data:
                products.append(resp.data)
            else:
                flash(f"El producto con ID {product_id} no está disponible.", 'error')
        except Exception as e:
            logger.error(f"Error consultando producto en wishlist {product_id}: {e}")
            flash(f"Error al consultar el producto con ID {product_id}.", 'error')
    return render_template('wishlist.html', products=products)

@cart_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    """
    Agrega un producto a la wishlist, verificando su existencia.
    """
    supabase = current_app.supabase
    try:
        resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
    except Exception as e:
        logger.error(f"Error al consultar producto {product_id} para wishlist: {e}")
        flash("Error al consultar la disponibilidad del producto.", 'error')
        return redirect(url_for('cart.view_wishlist'))
    
    if not resp.data:
        flash("El producto no está disponible.", 'error')
        return redirect(url_for('cart.view_wishlist'))
    
    wishlist_items = session.get('wishlist', [])
    if product_id in wishlist_items:
        flash("El producto ya está en la lista de deseos.", 'info')
    else:
        wishlist_items.append(product_id)
        flash("Producto agregado a la lista de deseos.", 'success')
    session['wishlist'] = wishlist_items
    return redirect(url_for('cart.view_wishlist'))

@cart_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    """
    Elimina un producto de la wishlist, con confirmación.
    """
    wishlist_items = session.get('wishlist', [])
    if product_id in wishlist_items:
        wishlist_items.remove(product_id)
        session['wishlist'] = wishlist_items
        flash("Producto eliminado de la lista de deseos.", 'success')
    else:
        flash("El producto no está en la lista de deseos.", 'error')
    return redirect(url_for('cart.view_wishlist'))
