import os
import logging
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, UserMixin, login_required

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

class AdminUser(UserMixin):
    def __init__(self, id, username):
        self.id = str(id)  # Flask-Login requiere que el id sea una cadena
        self.username = username

    @property
    def is_admin(self):
        return True

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Accediendo a la página de login")
    if request.method == 'POST':
        logger.debug("Procesando datos de login: %s", request.form)
        username = request.form.get('username')
        password = request.form.get('password')
        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")
        logger.debug("Comparando credenciales: recibido [%s] vs. esperado [%s]", username, admin_username)
        if username == admin_username and password == admin_password:
            user = AdminUser(1, username)
            login_user(user)
            flash("Bienvenido, administrador.", "success")
            logger.info("Usuario %s autenticado exitosamente", username)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.index'))
        else:
            flash("Credenciales inválidas.", "error")
            logger.warning("Intento fallido de login para usuario: %s", username)
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logger.info("Cerrando sesión del usuario %s", request.remote_addr)
    logout_user()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('auth.login'))
