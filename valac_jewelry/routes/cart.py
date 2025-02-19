# valac_jewelry/routes/cart.py
from flask import Blueprint, render_template, redirect, url_for, session, request, current_app

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

@cart_bp.route('/')
def view_cart():
    """
    Muestra los productos en el carrito (guardados en la sesión).
    """
    supabase = current_app.supabase
    cart_items = session.get('cart', [])
    
    # Opcional: traer info de los productos desde la BD para obtener precio, imagen, etc.
    # Si guardamos en sesión sólo IDs, aquí consultamos a la DB:
    products = []
    for item_id in cart_items:
        resp = supabase.table('products').select('*').eq('id', item_id).single().execute()
        if resp.data:
            products.append(resp.data)
    
    return render_template('cart.html', products=products)

@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    """
    Agrega un producto al carrito, guardándolo en la sesión.
    """
    cart_items = session.get('cart', [])
    if product_id not in cart_items:
        cart_items.append(product_id)
    session['cart'] = cart_items
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    """
    Elimina un producto del carrito.
    """
    cart_items = session.get('cart', [])
    if product_id in cart_items:
        cart_items.remove(product_id)
    session['cart'] = cart_items
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/wishlist')
def view_wishlist():
    """
    Ejemplo de wishlist (similar al carrito, pero lista separada).
    """
    supabase = current_app.supabase
    wishlist_items = session.get('wishlist', [])
    products = []
    for item_id in wishlist_items:
        resp = supabase.table('products').select('*').eq('id', item_id).single().execute()
        if resp.data:
            products.append(resp.data)
    return render_template('wishlist.html', products=products)

@cart_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    """
    Agrega un producto a la wishlist.
    """
    wishlist_items = session.get('wishlist', [])
    if product_id not in wishlist_items:
        wishlist_items.append(product_id)
    session['wishlist'] = wishlist_items
    return redirect(url_for('cart.view_wishlist'))

@cart_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    """
    Elimina un producto de la wishlist.
    """
    wishlist_items = session.get('wishlist', [])
    if product_id in wishlist_items:
        wishlist_items.remove(product_id)
    session['wishlist'] = wishlist_items
    return redirect(url_for('cart.view_wishlist'))
