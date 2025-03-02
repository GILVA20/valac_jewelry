from flask import Blueprint, render_template, request, redirect, flash, url_for

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Extraer datos del formulario
        nombre = request.form.get('nombre')
        direccion = request.form.get('direccion')
        ciudad = request.form.get('ciudad')
        codigo_postal = request.form.get('codigo_postal')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        metodo_pago = request.form.get('metodo_pago')
        # Aquí se pueden extraer y validar otros datos, como los de la tarjeta de crédito

        # Procesar la lógica de pago, actualizar inventario, enviar confirmación, etc.
        # Si todo es correcto:
        flash("Pago procesado con éxito. ¡Gracias por tu compra!", "success")
        return redirect(url_for('confirmation'))
        # En caso de error, podrías usar flash() para mostrar mensajes y redirigir nuevamente al checkout

    return render_template('checkout.html')
