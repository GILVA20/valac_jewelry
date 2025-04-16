from flask import Blueprint, render_template, request, redirect, flash, url_for

from flask import Blueprint, request, redirect, url_for, flash

contact_bp = Blueprint('contact', __name__, url_prefix='/contact')

@contact_bp.route('/', methods=['GET'])
def contact():
    return render_template('contact.html')

@contact_bp.route('/send', methods=['POST'])
def send():
    # Aquí procesas los datos del formulario
    # Por ejemplo, leer request.form['nombre'], etc.
    # y luego envías el correo o almacenas el mensaje, etc.
    flash("Mensaje enviado correctamente", "success")
    return redirect(url_for('contact.contact'))