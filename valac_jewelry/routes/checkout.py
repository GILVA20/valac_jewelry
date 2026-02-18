import os
import logging
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, session, jsonify
import mercadopago
from supabase import create_client, Client

def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or "0"))

def sanitize_input(input_str):
    return str(input_str).strip().replace("<", "&lt;").replace(">", "&gt;")

# ---------------- Supabase ----------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

checkout_bp = Blueprint('checkout', __name__)
log = logging.getLogger("valac_jewelry")

# ---------------- Helpers ----------------
def build_order_items_and_subtotal():
    """
    Construye items a partir del carrito en sesión y calcula subtotal
    leyendo precio vigente desde Supabase (precio_descuento si existe).
    """
    cart_data = session.get("cart", {}) or {}
    order_items = []
    subtotal = 0.0

    for product_id_str, quantity in cart_data.items():
        try:
            product_id = int(product_id_str)
            resp = supabase.table('products').select('*').eq('id', product_id).single().execute()
            if not resp.data:
                current_app.logger.error("Producto con ID %s no encontrado.", product_id)
                continue

            product = resp.data
            qty = int(quantity)
            product['cantidad'] = qty
            product.setdefault("descripcion", "Sin descripción")

            # unit_price: usa precio_descuento si viene, si no precio
            unit_price = float(product.get("precio_descuento", product.get("precio", 0)))
            product['unit_price'] = unit_price

            subtotal += unit_price * qty
            order_items.append(product)
        except Exception as e:
            current_app.logger.error("Error obteniendo producto %s: %s", product_id_str, e)

    return order_items, subtotal


def snapshot_totals_fallback(subtotal_calc: float) -> dict:
    """
    Usa session['cart_snapshot'] como FUENTE DE VERDAD de montos;
    si no existe, calcula shipping y totales como fallback.
    """
    snap = session.get("cart_snapshot") or {}
    if snap:
        return {
            "subtotal": float(snap.get("subtotalProducts", 0.0)),
            "shipping": float(snap.get("shipping", 0.0)),
            "discount": float(snap.get("discount_total", 0.0)),  # solo para UI; NO existe en DB
            "total": float(snap.get("total", 0.0)),
            "coupon_code": snap.get("coupon_code"),
            "coupon_percent_base": snap.get("coupon_percent_base", "products"),
        }
    # Fallback consistente con reglas del carrito
    shipping = 0.0 if subtotal_calc >= 8500 else (260.0 if subtotal_calc > 0 else 0.0)
    return {
        "subtotal": float(subtotal_calc),
        "shipping": float(shipping),
        "discount": 0.0,
        "total": float(subtotal_calc + shipping),
        "coupon_code": None,
        "coupon_percent_base": "products",
    }


def create_order_in_db(order_data, order_items):
    """
    Inserta en 'orders' usando EXACTAMENTE los nombres de columna del esquema:

      - dirección_envío (text, NOT NULL)
      - costo_envío     (numeric, NOT NULL)
      - método_pago     (text,    NULLABLE)
      - demás campos: ver tabla 'orders'

    También descarta claves que no existen en la tabla (coupon_*, discount_total).
    """
    # Claves que NO existen en orders (según tu esquema)
    DROP_KEYS = {"coupon_code", "coupon_percent_base", "discount_total"}

    payload = {k: v for k, v in order_data.items() if k not in DROP_KEYS}

    try:
        response = supabase.table("orders").insert(payload).execute()
        if not response.data:
            log.error("Error insertando la orden: %s", response)
            return None
        order_id = response.data[0]["id"]
        order_data["id"] = order_id
        session["order_data"] = order_data
        session["order_items"] = order_items
        return order_id
    except Exception as e:
        log.exception("Excepción insertando orden en Supabase: %s", e)
        return None


# ---------------- Route ----------------
@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # ---------- GET: mostrar resumen ----------
    if request.method == 'GET':
        order_items, subtotal_calc = build_order_items_and_subtotal()
        totals = snapshot_totals_fallback(subtotal_calc)

        # para compatibilidad con plantillas antiguas
        session['discount_amount'] = totals["discount"]

        # Crear preferencia de MercadoPago para mostrar el botón desde el inicio
        ENV = os.getenv("FLASK_ENV", "development").lower()
        IS_PROD = ENV == "production"
        
        # Forzar modo test en localhost
        if "localhost" in request.url_root or "127.0.0.1" in request.url_root:
            IS_PROD = False
            log.info("Forzando modo TEST porque estamos en localhost")
        
        token = (current_app.config["MP_ACCESS_TOKEN"] if IS_PROD else current_app.config["MP_ACCESS_TOKEN_TEST"])
        public_key = (current_app.config["MP_PUBLIC_KEY"] if IS_PROD else current_app.config["MP_PUBLIC_KEY_TEST"])
        
        log.info(f"Modo: {'PRODUCCION' if IS_PROD else 'TEST'}")
        log.info(f"Public Key: {public_key[:20]}..." if public_key else "Public Key: None")
        
        mp = mercadopago.SDK(token)

        # IMPORTANTE: Siempre usar URLs de producción para back_urls y notification_url
        # MercadoPago (incluso en sandbox) requiere URLs públicamente accesibles
        # Las URLs localhost (127.0.0.1) causan error 400 con auto_return
        base_url = "https://valacjoyas.com"
        back_urls = {
            "success": f"{base_url}/success",
            "failure": f"{base_url}/failure",
            "pending": f"{base_url}/pending",
        }
        notification_url = "https://valacjoyas.com/webhook"

        preference_data = {
            "items": [{
                "title": "Orden de Compra VALAC Joyas",
                "unit_price": float(totals["total"]),
                "quantity": 1
            }],
            "back_urls": back_urls,
            "auto_return": "approved",
            "notification_url": notification_url,
            "payment_methods": {
                "installments": 18,
                "default_installments": 6
            },
            "metadata": {"environment": "production" if IS_PROD else "sandbox"},
        }

        # Solo crear preferencia si hay productos en el carrito (total > 0)
        preference_response = None
        if totals["total"] > 0:
            preference_response = mp.preference().create(preference_data)
        
        preference_id = None
        init_point = None
        
        # Solo crear preferencia si hay productos en el carrito (total > 0)
        if totals["total"] > 0:
            log.info(f"Respuesta COMPLETA de MercadoPago: {preference_response}")
            
            if preference_response and "response" in preference_response:
                pref = preference_response["response"]
                log.info(f"Keys en response: {pref.keys()}")
                if "id" in pref:
                    preference_id = pref["id"]
                    # En sandbox, MercadoPago devuelve sandbox_init_point
                    # En producción, devuelve init_point
                    init_point = pref.get("sandbox_init_point") or pref.get("init_point")
                    log.info(f"Preference ID creado: {preference_id}")
                    log.info(f"sandbox_init_point: {pref.get('sandbox_init_point')}")
                    log.info(f"init_point: {pref.get('init_point')}")
                    log.info(f"Init Point final: {init_point}")
                else:
                    log.error(f"No se encontró 'id' en la respuesta: {pref}")
            else:
                log.error(f"Respuesta inválida de MercadoPago: {preference_response}")
        else:
            log.warning("Carrito vacío - no se puede crear preferencia de MercadoPago")

        if not preference_id:
            log.warning("No se pudo crear preference_id, el botón de MP no se mostrará")

        return render_template(
            'checkout_luxury.html',
            current_step=3,
            order_items=order_items,
            subtotal=totals["subtotal"],
            shipping=totals["shipping"],
            discount=totals["discount"],
            total=totals["total"],
            coupon_code=totals["coupon_code"],
            coupon_percent_base=totals["coupon_percent_base"],
            preference_id=preference_id,
            mp_public_key=public_key,
            mp_init_point=init_point,
        )

    # ---------- POST: procesar pago ----------
    # Extraer y sanitizar datos del formulario
    nombre = sanitize_input(request.form.get('nombre'))
    direccion_envio_in = sanitize_input(request.form.get('direccion'))
    estado_envio = sanitize_input(request.form.get('estado'))
    colonia = sanitize_input(request.form.get('colonia'))
    ciudad = sanitize_input(request.form.get('ciudad'))
    codigo_postal = sanitize_input(request.form.get('codigo_postal'))
    telefono = sanitize_input(request.form.get('telefono'))
    email = sanitize_input(request.form.get('email'))

    metodo_pago_in = (request.form.get('metodo_pago', '').strip().lower())
    if metodo_pago_in == "mercadopago":
        metodo_pago_in = "MercadoPago"
    elif metodo_pago_in == "aplazo":
        metodo_pago_in = "aplazo"
    elif metodo_pago_in == "mock_gateway":
        metodo_pago_in = "mock_gateway"
    metodo_pago_in = sanitize_input(metodo_pago_in)

    # Normaliza estado
    estado_mapping = {"hi": "Hidalgo", "hidalgo": "Hidalgo"}
    estado_geografico = estado_mapping.get(estado_envio.lower(), estado_envio)

    if not all([nombre, direccion_envio_in, estado_geografico, colonia, ciudad, codigo_postal, telefono, email, metodo_pago_in]):
        flash("Por favor, completa todos los campos obligatorios.", "error")
        return redirect(url_for('checkout.checkout'))

    # Ítems + totales del snapshot (FUENTE DE VERDAD)
    order_items, subtotal_calc = build_order_items_and_subtotal()
    if not order_items:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for('cart.view_cart'))

    totals = snapshot_totals_fallback(subtotal_calc)
    subtotal = totals["subtotal"]
    shipping_cost = totals["shipping"]
    discount = totals["discount"]  # solo UI
    total = totals["total"]

    # ---------- Datos de la orden (nombres EXACTOS según tu tabla) ----------
    # Nota: tu esquema usa acentos:
    #   dirección_envío (NOT NULL)
    #   costo_envío     (NOT NULL)
    #   método_pago     (NULLABLE – pero enviamos valor)
    order_data = {
        "nombre": nombre,
        "dirección_envío": direccion_envio_in,
        "estado_geografico": estado_geografico or None,  # nullable en DB
        "colonia": colonia,  # nullable en DB, pero enviamos lo que viene
        "ciudad": ciudad,
        "codigo_postal": codigo_postal,
        "telefono": telefono,
        "email": email,
        "método_pago": metodo_pago_in,    # con acento, como en la tabla
        "subtotal": subtotal,
        "costo_envío": shipping_cost,     # con acento, como en la tabla
        "total": total,
        "estado_pago": "Pendiente",       # existe y por defecto es 'Pendiente'
        # Campos que NO existen en DB no se incluyen (coupon_*, discount_total)
    }

    order_id = create_order_in_db(order_data, order_items)
    if not order_id:
        flash("Error registrando la orden (verifica columnas acentuadas y tipos).", "error")
        return redirect(url_for('checkout.checkout'))

    # Validar método de pago
    if metodo_pago_in not in ["MercadoPago", "aplazo", "mock_gateway"]:
        flash("Método de pago no válido. Selecciona MercadoPago, Aplazo o Pago Simulado.", "error")
        return redirect(url_for('checkout.checkout'))

    # ------- MercadoPago -------
    if metodo_pago_in == "MercadoPago":
        simular_pago = os.getenv("SIMULAR_PAGO", "False").lower() == "true"
        if simular_pago:
            simulated_status = {"estado_pago": "Completado", "transaction_id": "SIMULADO", "fecha_actualizacion": "now()"}
            supabase.table("orders").update(simulated_status).eq("id", order_id).execute()
            flash("Pago simulado con éxito. Orden completada.", "success")
            return redirect(url_for('success.success'))

        ENV = os.getenv("FLASK_ENV", "development").lower()
        IS_PROD = ENV == "production"

        token = (current_app.config["MP_ACCESS_TOKEN"] if IS_PROD else current_app.config["MP_ACCESS_TOKEN_TEST"])
        mp = mercadopago.SDK(token)

        base_url = "https://valacjoyas.com" if IS_PROD else request.url_root.rstrip('/')
        back_urls = {
            "success": f"{base_url}/success",
            "failure": f"{base_url}/failure",
            "pending": f"{base_url}/pending",
        }
        notification_url = "https://valacjoyas.com/webhook"

        # MUY IMPORTANTE: usar el total del snapshot (ya con descuento aplicado)
        preference_data = {
            "items": [{
                "title": "Orden de Compra VALAC Joyas",
                "unit_price": float(total),
                "quantity": 1
            }],
            "back_urls": back_urls,
            "notification_url": notification_url,
            "payment_methods": {
                "installments": 18,
                "default_installments": 6
            },
            "metadata": {"environment": "production" if IS_PROD else "sandbox"},
            "external_reference": str(order_id)
        }
        if IS_PROD:
            preference_data["auto_return"] = "approved"

        preference_response = mp.preference().create(preference_data)
        if not preference_response or "response" not in preference_response:
            current_app.logger.error("Respuesta inválida de MercadoPago: %s", preference_response)
            flash("Error en la respuesta de MercadoPago, por favor inténtalo nuevamente.", "error")
            return redirect(url_for('checkout.checkout'))

        pref = preference_response["response"]
        if "id" not in pref:
            current_app.logger.error("Preferencia sin 'id'. Respuesta: %s", pref)
            flash("Error al crear la preferencia de pago.", "error")
            return redirect(url_for('checkout.checkout'))

        preference_id = pref["id"]
        return render_template(
            "mercadopago_checkout.html",
            preference_id=preference_id,
            MP_PUBLIC_KEY=current_app.config["MP_PUBLIC_KEY"],
            subtotal=subtotal,
            shipping=shipping_cost,
            discount=discount,
            total=total,
            sandbox=(not IS_PROD),
            coupon_percent_base=totals.get("coupon_percent_base", "products"),
            coupon_code=totals.get("coupon_code"),
        )

    # ------- Aplazo -------
    if metodo_pago_in == "aplazo":
        flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
        return redirect(url_for('success.success'))

    # ------- Mock / Simulado -------
    if metodo_pago_in == "mock_gateway":
        return redirect(url_for('mock_checkout.index', order_id=order_id))

    # Fallback
    return redirect(url_for('checkout.checkout'))


@checkout_bp.route('/api/create-preference', methods=['POST'])
def create_preference():
    """
    API endpoint para crear preferencia de MercadoPago desde el frontend.
    Devuelve el preference_id y public_key para renderizar el Wallet Button.
    """
    try:
        # Extraer datos del request JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400

        # Validar campos requeridos
        required_fields = ['nombre', 'direccion', 'codigo_postal', 'telefono', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Campo '{field}' es requerido"}), 400

        # Sanitizar datos
        nombre = sanitize_input(data.get('nombre'))
        direccion_envio_in = sanitize_input(data.get('direccion'))
        estado_envio = sanitize_input(data.get('estado', 'México'))
        colonia = sanitize_input(data.get('colonia', '-'))
        ciudad = sanitize_input(data.get('ciudad', '-'))
        codigo_postal = sanitize_input(data.get('codigo_postal'))
        telefono = sanitize_input(data.get('telefono'))
        email = sanitize_input(data.get('email'))

        # Normalizar estado
        estado_mapping = {"hi": "Hidalgo", "hidalgo": "Hidalgo"}
        estado_geografico = estado_mapping.get(estado_envio.lower(), estado_envio)

        # Construir orden
        order_items, subtotal_calc = build_order_items_and_subtotal()
        if not order_items:
            return jsonify({"error": "El carrito está vacío"}), 400

        totals = snapshot_totals_fallback(subtotal_calc)
        subtotal = totals["subtotal"]
        shipping_cost = totals["shipping"]
        total = totals["total"]

        # Crear orden en DB
        order_data = {
            "nombre": nombre,
            "dirección_envío": direccion_envio_in,
            "estado_geografico": estado_geografico or None,
            "colonia": colonia,
            "ciudad": ciudad,
            "codigo_postal": codigo_postal,
            "telefono": telefono,
            "email": email,
            "método_pago": "MercadoPago",
            "subtotal": subtotal,
            "costo_envío": shipping_cost,
            "total": total,
            "estado_pago": "Pendiente",
        }

        order_id = create_order_in_db(order_data, order_items)
        if not order_id:
            return jsonify({"error": "Error al crear la orden"}), 500

        # Determinar ambiente
        ENV = os.getenv("FLASK_ENV", "development").lower()
        IS_PROD = ENV == "production"
        token = (current_app.config["MP_ACCESS_TOKEN"] if IS_PROD else current_app.config["MP_ACCESS_TOKEN_TEST"])
        public_key = (current_app.config["MP_PUBLIC_KEY"] if IS_PROD else current_app.config["MP_PUBLIC_KEY_TEST"])
        
        mp = mercadopago.SDK(token)

        base_url = "https://valacjoyas.com" if IS_PROD else request.url_root.rstrip('/')
        back_urls = {
            "success": f"{base_url}/success",
            "failure": f"{base_url}/failure",
            "pending": f"{base_url}/pending",
        }
        notification_url = "https://valacjoyas.com/webhook"

        # Crear preferencia
        preference_data = {
            "items": [{
                "title": "Orden de Compra VALAC Joyas",
                "unit_price": float(total),
                "quantity": 1
            }],
            "back_urls": back_urls,
            "notification_url": notification_url,
            "payment_methods": {
                "installments": 18,
                "default_installments": 6
            },
            "metadata": {"environment": "production" if IS_PROD else "sandbox"},
            "external_reference": str(order_id)
        }
        
        if IS_PROD:
            preference_data["auto_return"] = "approved"

        preference_response = mp.preference().create(preference_data)
        if not preference_response or "response" not in preference_response:
            log.error("Respuesta inválida de MercadoPago: %s", preference_response)
            return jsonify({"error": "Error al crear la preferencia de pago"}), 500

        pref = preference_response["response"]
        if "id" not in pref:
            log.error("Preferencia sin 'id'. Respuesta: %s", pref)
            return jsonify({"error": "Error al crear la preferencia de pago"}), 500

        preference_id = pref["id"]
        
        return jsonify({
            "preference_id": preference_id,
            "public_key": public_key,
            "order_id": order_id
        }), 200

    except Exception as e:
        log.exception("Error en create_preference API: %s", e)
        return jsonify({"error": "Error al procesar el pago. Por favor, inténtalo de nuevo."}), 500
