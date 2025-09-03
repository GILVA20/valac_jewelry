# valac_jewelry/routes/cart.py
from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, session, current_app, flash, request, jsonify
from functools import wraps
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import uuid4
import logging

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')
logger = logging.getLogger(__name__)

# =========================
# Utilidades de dinero/fechas
# =========================
def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or "0"))

def _round2(x) -> Decimal:
    return _dec(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _get_cart_id() -> str:
    if "cart_id" not in session:
        session["cart_id"] = str(uuid4())
    return session["cart_id"]

def _parse_utc(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc)
    # asume ISO 8601 string
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)

def is_coupon_active(coupon: dict, now_utc: datetime | None = None) -> bool:
    """Activo + dentro de la vigencia."""
    if not coupon or not bool(coupon.get("active", True)):
        return False
    now = now_utc or datetime.now(timezone.utc)
    starts = _parse_utc(coupon.get("starts_at"))
    ends   = _parse_utc(coupon.get("ends_at"))
    if not starts or not ends:
        return False
    return starts <= now <= ends

def apply_coupon(base_amount: Decimal, coupon: dict, msi_selected: bool = False) -> Decimal:
    """
    Aplica el cupón a 'base_amount' respetando:
    - coupon['type']: 'percent' | 'fixed'
    - coupon['value']
    - coupon['cap_mode']: 'amount' | 'percent' | 'both' | None
    - caps *_msi cuando aplique
    """
    base = _dec(base_amount)
    if base <= 0 or not coupon:
        return _dec(0)

    ctype = (coupon.get("type") or "").lower()
    value = _dec(coupon.get("value") or 0)

    raw = base * (value / _dec(100)) if ctype == "percent" else value

    cap_mode = (coupon.get("cap_mode") or "both").lower()
    cap_amt  = coupon.get("cap_amount")
    cap_pct  = coupon.get("cap_percent")

    # caps MSI si los hubiera
    if msi_selected:
        if coupon.get("cap_amount_msi") is not None:
            cap_amt = coupon.get("cap_amount_msi")
        if coupon.get("cap_percent_msi") is not None:
            cap_pct = coupon.get("cap_percent_msi")

    caps = []
    if cap_mode in ("amount", "both") and cap_amt not in (None, 0, "0"):
        caps.append(_dec(cap_amt))
    if cap_mode in ("percent", "both") and cap_pct not in (None, 0, "0"):
        caps.append(base * (_dec(cap_pct) / _dec(100)))

    disc = raw if not caps else min(raw, *caps)
    disc = max(_dec(0), min(disc, base))
    return _round2(disc)

def compute_totals(
    items: list[dict],
    shipping_base: Decimal,
    free_shipping_threshold: Decimal,
    coupon: dict | None = None,
    msi_selected: bool = False,
    coupon_percent_base: str = "products",  # 'products' | 'products_plus_shipping'
) -> dict:
    """
    items: [{id, name, unit_price, quantity}]
    Retorna breakdown calculado en el servidor.
    """
    subtotal_products = _round2(sum(_dec(i["unit_price"]) * _dec(i["quantity"]) for i in items))

    # Envío
    if subtotal_products == 0:
        shipping = _dec(0)
    elif subtotal_products >= _dec(free_shipping_threshold):
        shipping = _dec(0)
    else:
        shipping = _round2(shipping_base)

    pre_coupon = _round2(subtotal_products + shipping)

    base_for_coupon = pre_coupon if coupon_percent_base == "products_plus_shipping" else subtotal_products

    discount_total = _dec(0)
    if coupon and is_coupon_active(coupon):
        discount_total = apply_coupon(base_for_coupon, coupon, msi_selected)

    total = _round2(pre_coupon - discount_total)

    return {
        "subtotalProducts": _round2(subtotal_products),
        "shipping": _round2(shipping),
        "preCoupon": _round2(pre_coupon),
        "discount_total": _round2(discount_total),
        "total": _round2(total),
    }

# =========================
# Helpers de Carrito (sesión)
# =========================
def get_cart_data() -> dict[str, int]:
    cart_data = session.get('cart', {})
    if not isinstance(cart_data, dict):
        cart_data = {}
    return {str(k): int(v) for k, v in cart_data.items() if str(k).isdigit()}

def cart_not_empty(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_cart_data():
            flash("Tu carrito está vacío.", 'warning')
            return redirect(url_for('cart.view_cart'))
        return f(*args, **kwargs)
    return wrapper

# =========================
# Rutas
# =========================
@cart_bp.route('/')
def view_cart():
    """
    Renderiza el carrito. El servidor calcula montos (fuente de verdad).
    """
    sb = current_app.supabase
    cart_data = get_cart_data()

    FREE_SHIPPING_THRESHOLD = _dec(current_app.config.get("FREE_SHIPPING_THRESHOLD", 8500))
    SHIPPING_BASE = _dec(current_app.config.get("SHIPPING_BASE", 260))
    COUPON_PERCENT_BASE = str(current_app.config.get("COUPON_PERCENT_BASE", "products"))

    if not cart_data:
        session.pop("cart_snapshot", None)
        flash("No hay productos en el carrito.", 'info')
        return render_template(
            'cart.html',
            products=[],
            shipping_base=float(SHIPPING_BASE),
            free_shipping_threshold=float(FREE_SHIPPING_THRESHOLD),
        )

    # Carga productos vigentes
    products = []
    for product_key, quantity in cart_data.items():
        try:
            pid = int(product_key)
            resp = sb.table('products').select(
                'id,nombre,precio,descuento_pct,precio_descuento,stock_total,imagen'
            ).eq('id', pid).single().execute()
            row = resp.data
            if not row:
                flash(f"El producto con ID {pid} no está disponible.", 'error')
                continue

            # Validación simple de stock (si existe el campo)
            if row.get('stock_total') is not None and int(row['stock_total']) < int(quantity):
                flash(f"El producto '{row.get('nombre','desconocido')}' no tiene suficiente stock.", 'error')

            pct = row.get('descuento_pct') or 0
            unit_price = float(row['precio_descuento']) if (pct and row.get('precio_descuento') is not None) else float(row['precio'])

            products.append({
                **row,
                "cantidad": int(quantity),
                "unit_price": unit_price
            })
        except Exception as e:
            logger.exception("Error consultando producto %s: %s", product_key, e)
            flash(f"Error al consultar el producto con ID {product_key}.", 'error')

    # Normaliza para cálculo
    items = [
        {
            "id": p["id"],
            "name": p.get("nombre") or f"Producto {p['id']}",
            "unit_price": Decimal(str(p["unit_price"])),
            "quantity": int(p["cantidad"]),
        }
        for p in products
    ]

    # Recupera cupón guardado en sesión (si existe y sigue vigente en DB)
    cart_id = _get_cart_id()
    coupon_info = session.get("coupon_info")
    coupon_row = None
    if coupon_info and coupon_info.get("cart_id") == cart_id:
        try:
            code = coupon_info.get("code")
            r = sb.table("coupons").select("*").eq("code", code).single().execute()
            coupon_row = r.data or None
        except Exception:
            coupon_row = None
        # Si ya no está activo o fuera de vigencia, lo descartamos
        if coupon_row and not is_coupon_active(coupon_row):
            coupon_row = None
            session.pop("coupon_info", None)

    # MSI (si aplica en tu checkout; aquí False por default)
    msi_selected = False

    totals = compute_totals(
        items=items,
        shipping_base=SHIPPING_BASE,
        free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
        coupon=coupon_row,
        msi_selected=msi_selected,
        coupon_percent_base=COUPON_PERCENT_BASE,
    )

    snapshot = {
        "cart_id": cart_id,
        "items": [
            {
                "id": it["id"],
                "name": it["name"],
                "unit_price": float(_round2(it["unit_price"])),
                "quantity": int(it["quantity"]),
            } for it in items
        ],
        "subtotalProducts": float(totals["subtotalProducts"]),
        "shipping": float(totals["shipping"]),
        "preCoupon": float(totals["preCoupon"]),
        "discount_total": float(totals["discount_total"]),
        "total": float(totals["total"]),
        "coupon_code": coupon_info["code"] if coupon_row else None,
        "msi_selected": msi_selected,
        "coupon_percent_base": COUPON_PERCENT_BASE,
    }
    session["cart_snapshot"] = snapshot

    return render_template(
        'cart.html',
        products=products,
        shipping_base=float(SHIPPING_BASE),
        free_shipping_threshold=float(FREE_SHIPPING_THRESHOLD),
        subtotalProducts=snapshot["subtotalProducts"],
        shipping_amount=snapshot["shipping"],
        preCoupon=snapshot["preCoupon"],
        discount_total=snapshot["discount_total"],
        total=snapshot["total"],
        coupon_percent_base=COUPON_PERCENT_BASE,
        coupon_code=snapshot["coupon_code"],
    )

@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id: int):
    sb = current_app.supabase
    try:
        resp = sb.table('products').select('id').eq('id', product_id).single().execute()
        if not resp.data:
            flash("El producto no está disponible.", 'error')
            return redirect(url_for('cart.view_cart'))
    except Exception as e:
        logger.error("Error al consultar producto %s: %s", product_id, e)
        flash("Error al consultar la disponibilidad del producto.", 'error')
        return redirect(url_for('cart.view_cart'))

    cart_data = get_cart_data()
    key = str(product_id)
    cart_data[key] = cart_data.get(key, 0) + 1
    session['cart'] = cart_data
    flash("Producto agregado al carrito.", 'success')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id: int):
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
# Cupón: aplicar / remover (sin hardcode)
# =========================
@cart_bp.route('/coupon/apply', methods=['POST'])
def cart_apply_coupon():
    """
    Guarda el cupón en sesión (validando contra DB). No calcula el monto aquí.
    """
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"ok": False, "reason": "invalid"}), 400

    sb = current_app.supabase
    try:
        r = sb.table("coupons").select("*").eq("code", code).single().execute()
        coupon = r.data or None
    except Exception as e:
        current_app.logger.error("Error leyendo cupón %s: %s", code, e)
        return jsonify({"ok": False, "reason": "server_error"}), 500

    if not coupon:
        return jsonify({"ok": False, "reason": "invalid"}), 200
    if not is_coupon_active(coupon):
        return jsonify({"ok": False, "reason": "inactive"}), 200

    # opcional: aquí podrías validar min_order, límites, etc. igual que /api/coupons/validate

    cart_id = _get_cart_id()
    session["coupon_info"] = {
        "cart_id": cart_id,
        "code": code,      # sólo guardamos el código; en view_cart se vuelve a leer la fila de DB
    }
    return jsonify({"ok": True, "code": code})

@cart_bp.route('/coupon/remove', methods=['POST'])
def cart_remove_coupon():
    cart_id = _get_cart_id()
    existing = session.get("coupon_info")
    if existing and existing.get("cart_id") == cart_id:
        session.pop("coupon_info", None)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "reason": "no_coupon"}), 404

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
