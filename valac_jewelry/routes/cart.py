from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, session, current_app, flash, request
from functools import wraps
import logging

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')
logger = logging.getLogger(__name__)

# =========================
# Helpers
# =========================
def get_cart_data():
    """
    Devuelve el carrito desde sesión como dict {str(product_id): int(cantidad)}.
    Siempre normaliza a dict con claves string.
    """
    cart_data = session.get('cart', {})
    if not isinstance(cart_data, dict):
        cart_data = {}
    return {str(k): int(v) for k, v in cart_data.items() if str(k).isdigit()}

def cart_not_empty(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_cart_data():
            flash("Tu carrito está vacío.", 'warning')
            return redirect(url_for('cart.view_cart'))
        return f(*args, **kwargs)
    return decorated_function


# =========================
# Rutas de Carrito
# =========================
@cart_bp.route('/')
def view_cart():
    """
    Muestra los productos en el carrito.
    La sesión almacena el carrito como un dict {producto_id(str): cantidad(int)}.
    Se consulta Supabase para poblar datos actuales de cada producto.
    """
    sb = current_app.supabase
    cart_data = get_cart_data()

    # Config de envío desde la app (con defaults razonables)
    FREE_SHIPPING_THRESHOLD = current_app.config.get("FREE_SHIPPING_THRESHOLD", 8500)
    SHIPPING_BASE = current_app.config.get("SHIPPING_BASE", 260)

    if not cart_data:
        flash("No hay productos en el carrito.", 'info')
        return render_template(
            'cart.html',
            products=[],
            shipping_base=SHIPPING_BASE,
            free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
        )

    products = []
    for product_key, quantity in cart_data.items():
        try:
            pid = int(product_key)
            resp = sb.table('products').select('*').eq('id', pid).single().execute()
            if not resp.data:
                flash(f"El producto con ID {pid} no está disponible.", 'error')
                continue

            row = resp.data

            # Si tu tabla maneja stock_total a nivel producto:
            if 'stock_total' in row and row['stock_total'] is not None and int(row['stock_total']) < quantity:
                flash(f"El producto '{row.get('nombre', 'desconocido')}' no tiene suficiente stock.", 'error')

            # Precio a cobrar por unidad (considera precio_descuento si hay % aplicado)
            pct = row.get('descuento_pct') or 0
            unit_price = float(row['precio_descuento']) if (pct and row.get('precio_descuento') is not None) else float(row['precio'])

            prod = {
                **row,
                "cantidad": int(quantity),
                "unit_price": unit_price
            }
            products.append(prod)

        except Exception as e:
            logger.exception("Error consultando producto %s: %s", product_key, e)
            flash(f"Error al consultar el producto con ID {product_key}.", 'error')

    return render_template(
        'cart.html',
        products=products,
        shipping_base=SHIPPING_BASE,
        free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
    )


@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id: int):
    """
    Agrega un producto al carrito (cantidad += 1).
    Verifica existencia del producto.
    """
    sb = current_app.supabase
    try:
        resp = sb.table('products').select('id, nombre, precio, descuento_pct, precio_descuento').eq('id', product_id).single().execute()
    except Exception as e:
        logger.error("Error al consultar producto %s: %s", product_id, e)
        flash("Error al consultar la disponibilidad del producto.", 'error')
        return redirect(url_for('cart.view_cart'))

    if not resp.data:
        flash("El producto no está disponible.", 'error')
        return redirect(url_for('cart.view_cart'))

    cart_data = get_cart_data()
    key = str(product_id)
    cart_data[key] = cart_data.get(key, 0) + 1
    session['cart'] = cart_data
    flash("Producto agregado al carrito.", 'success')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id: int):
    """
    Elimina un producto del carrito (completo).
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
def update_quantity(product_id: int):
    """
    Actualiza la cantidad de un producto en el carrito.
    Cantidad <= 0 elimina el producto.
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


# =========================
# Wishlist (simple)
# =========================
@cart_bp.route('/wishlist')
def view_wishlist():
    sb = current_app.supabase
    wishlist_items = session.get('wishlist', [])
    if not wishlist_items:
        flash("No hay productos en tu lista de deseos.", 'info')
        return render_template('wishlist.html', products=[])

    products = []
    for product_id in wishlist_items:
        try:
            resp = sb.table('products').select('*').eq('id', product_id).single().execute()
            if resp.data:
                products.append(resp.data)
            else:
                flash(f"El producto con ID {product_id} no está disponible.", 'error')
        except Exception as e:
            logger.error("Error consultando producto en wishlist %s: %s", product_id, e)
            flash(f"Error al consultar el producto con ID {product_id}.", 'error')

    return render_template('wishlist.html', products=products)


@cart_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id: int):
    sb = current_app.supabase
    try:
        resp = sb.table('products').select('id').eq('id', product_id).single().execute()
    except Exception as e:
        logger.error("Error al consultar producto %s para wishlist: %s", product_id, e)
        flash("Error al consultar la disponibilidad del producto.", 'error')
        return redirect(url_for('cart.view_wishlist'))

    if not resp.data:
        flash("El producto no está disponible.", 'error')
        return redirect(url_for('cart.view_wishlist'))

    wishlist = session.get('wishlist', [])
    if product_id in wishlist:
        flash("El producto ya está en la lista de deseos.", 'info')
    else:
        wishlist.append(product_id)
        flash("Producto agregado a la lista de deseos.", 'success')
    session['wishlist'] = wishlist
    return redirect(url_for('cart.view_wishlist'))


@cart_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id: int):
    wishlist = session.get('wishlist', [])
    if product_id in wishlist:
        wishlist.remove(product_id)
        session['wishlist'] = wishlist
        flash("Producto eliminado de la lista de deseos.", 'success')
    else:
        flash("El producto no está en la lista de deseos.", 'error')
    return redirect(url_for('cart.view_wishlist'))
