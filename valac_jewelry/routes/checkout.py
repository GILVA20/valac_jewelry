import json
import os 
from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, session
import mercadopago

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Extraer datos del formulario (incluyendo los nuevos campos 'estado' y 'colonia')
        nombre = request.form.get('nombre')
        direccion_envio = request.form.get('direccion')
        estado = request.form.get('estado')
        colonia = request.form.get('colonia')
        ciudad = request.form.get('ciudad')
        codigo_postal = request.form.get('codigo_postal')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        metodo_pago = request.form.get('metodo_pago')
        
        # Validar que todos los campos obligatorios estén completos (incluyendo 'estado' y 'colonia')
        if not all([nombre, direccion_envio, estado, colonia, ciudad, codigo_postal, telefono, email, metodo_pago]):
            flash("Por favor, completa todos los campos obligatorios.", "error")
            return redirect(url_for('checkout.checkout'))
        
        # Simulación: calcular subtotal según productos en el carrito
        subtotal = 5000.00  
        # Calcular costo de envío: envío gratis si subtotal >= 6000; de lo contrario, $250 MXN
        shipping_cost = 0 if subtotal >= 6000 else 250
        total = subtotal + shipping_cost

        # Almacenamiento en la sesión de los datos reales de la orden
        order_data = {
            "nombre": nombre,
            "dirección_envío": direccion_envio,
            "estado": estado,
            "colonia": colonia,
            "ciudad": ciudad,
            "codigo_postal": codigo_postal,
            "telefono": telefono,
            "email": email,
            "método_pago": metodo_pago,
            "subtotal": subtotal,
            "costo_envío": shipping_cost,
            "total": total
        }
        # Obtener los ítems del carrito (si existen) o una lista vacía
        order_items = session.get("cart_items", [])
        
        # Guardar en la sesión los datos de la orden y la lista de ítems
        session["order_data"] = order_data
        session["order_items"] = order_items
        
        # Validar método de pago
        if metodo_pago not in ["mercadopago", "aplazo"]:
            flash("Método de pago no válido. Selecciona MercadoPago o Aplazo.", "error")
            return redirect(url_for('checkout.checkout'))
        
        if metodo_pago == "mercadopago":
            # Integración con MercadoPago Checkout Pro
            mp = mercadopago.SDK(current_app.config["MP_ACCESS_TOKEN"])
            preference_data = {
                "items": [{
                    "title": "Orden de Compra VALAC Joyas",
                    "unit_price": total,
                    "quantity": 1
                }],
                "back_urls": {
                    "success": "https://tu-dominio.com/success",
                    "failure": "https://tu-dominio.com/failure",
                    "pending": "https://tu-dominio.com/pending"
                },
                "auto_return": "approved",
                "notification_url": "https://tu-dominio.com/webhook"
            }
            preference_response = mp.preference().create(preference_data)
            preference = preference_response["response"]
            preference_id = preference["id"]

            # Renderizar plantilla que carga el Checkout Pro de MercadoPago
            return render_template(
                "mercadopago_checkout.html",
                preference_id=preference_id,
                MP_PUBLIC_KEY=os.getenv("MP_PUBLIC_KEY")
            )
        else:
            # Si se selecciona "aplazo", se simula el pago (o se integra la lógica correspondiente)
            pago_exitoso = True  # Simulación del pago exitoso
            if pago_exitoso:
                flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
                return redirect(url_for('confirmation'))
            else:
                flash("Error al procesar el pago. Intenta nuevamente.", "error")
                return redirect(url_for('checkout.checkout'))
    
    # Si es GET, renderizar el formulario de checkout
    return render_template('checkout.html')
