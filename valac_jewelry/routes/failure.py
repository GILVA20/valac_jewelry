import os
from flask import Blueprint, render_template, flash, redirect, url_for

failure_bp = Blueprint('failure', __name__)

@failure_bp.route('/failure')
def failure():
    """
    Se invoca cuando el pago es rechazado.
    Se muestra un mensaje de error al usuario.
    """
    flash("El pago ha sido rechazado. Por favor, inténtalo de nuevo.", "error")
    # Aquí podrías limpiar datos de sesión o redirigir a un formulario de reintento.
    return render_template("order_failure.html")
