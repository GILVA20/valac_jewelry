import json
import os
from flask import Blueprint, render_template, request, redirect, flash, url_for, current_app, session
import mercadopago
from supabase import create_client, Client  # Asegúrate de tener instalado supabase-py

# Configuración Supabase (asegúrate de definir SUPABASE_URL y SUPABASE_KEY en tu entorno)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

checkout_bp = Blueprint('checkout', __name__)

def create_order_in_db(order_data, order_items):
    """
    Inserta la orden en Supabase.
    Se asume que la tabla "orders" tiene un 'id' autogenerado y 'estado_pago' por defecto 'Pendiente'.
    Retorna el order_id generado.
    """
    response = supabase.table("orders").insert(order_data).execute()
    if response.error:
        print("Error insertando la orden:", response.error)
        return None
    order_id = response.data[0]["id"]
    order_data["id"] = order_id
    session["order_data"] = order_data  # Para prellenar el formulario en caso de reintentos
    session["order_items"] = order_items
    return order_id

@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Extraer datos del formulario (incluyendo 'estado' y 'colonia')
        nombre = request.form.get('nombre')
        direccion_envio = request.form.get('direccion')
        estado_envio = request.form.get('estado')
        colonia = request.form.get('colonia')
        ciudad = request.form.get('ciudad')
        codigo_postal = request.form.get('codigo_postal')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        metodo_pago = request.form.get('metodo_pago')
        
        # Validar campos obligatorios
        if not all([nombre, direccion_envio, estado_envio, colonia, ciudad, codigo_postal, telefono, email, metodo_pago]):
            flash("Por favor, completa todos los campos obligatorios.", "error")
            return redirect(url_for('checkout.checkout'))
        
        # Calcular subtotal y costo de envío (simulado)
        subtotal = 5000.00  
        shipping_cost = 0 if subtotal >= 6000 else 250
        total = subtotal + shipping_cost

        # Preparar datos de la orden (asegúrate de mapear correctamente los nombres de columna)
        order_data = {
            "nombre": nombre,
            "dirección_envío": direccion_envio,
            "estado": estado_envio,
            "colonia": colonia,
            "ciudad": ciudad,
            "codigo_postal": codigo_postal,
            "telefono": telefono,
            "email": email,
            "método_pago": metodo_pago,
            "subtotal": subtotal,
            "costo_envío": shipping_cost,
            "total": total,
            "estado_pago": "Pendiente"  # Estado inicial
        }
        order_items = session.get("cart_items", [])
        
        # Registrar la orden en Supabase
        order_id = create_order_in_db(order_data, order_items)
        if not order_id:
            flash("Error registrando la orden.", "error")
            return redirect(url_for('checkout.checkout'))
        
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
                "external_reference": str(order_id),
                "back_urls": {
                    "success": "https://valacjoyas.com/success",
                    "failure": "https://valacjoyas.com/failure",
                    "pending": "https://valacjoyas.com/pending"
                },
                "auto_return": "approved",
                "notification_url": "https://valacjoyas.com/webhook"
            }
            preference_response = mp.preference().create(preference_data)
            preference = preference_response["response"]
            preference_id = preference["id"]

            # Renderizamos la plantilla para redirigir a MercadoPago
            return render_template(
                "mercadopago_checkout.html",
                preference_id=preference_id,
                MP_PUBLIC_KEY=os.getenv("MP_PUBLIC_KEY")
            )
        else:
            # Flujo para "aplazo" (simulado)
            pago_exitoso = True  # Simulación del pago
            if pago_exitoso:
                flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
                return redirect(url_for('confirmation'))
            else:
                flash("Error al procesar el pago. Intenta nuevamente.", "error")
                return redirect(url_for('checkout.checkout'))
    
    return render_template('checkout.html')
