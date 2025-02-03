# valac_jewelry/routes/admin.py
from flask import Blueprint, render_template, request, Response, current_app, redirect, url_for, flash
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def check_auth(username, password):
    """Verifica si las credenciales son correctas."""
    return username == current_app.config.get('ADMIN_USERNAME') and password == current_app.config.get('ADMIN_PASSWORD')

def authenticate():
    """Envía un mensaje 401 para forzar el inicio de sesión."""
    return Response(
        'Acceso no autorizado. Por favor, proporciona credenciales válidas.\n', 
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@requires_auth
def admin_dashboard():
    # Una página inicial para el área administrativa
    return render_template('admin/dashboard.html')

@admin_bp.route('/upload', methods=['GET', 'POST'])
@requires_auth
def upload_item():
    if request.method == 'POST':
        # Aquí capturas los datos del formulario
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio')
        categoria = request.form.get('categoria')
        # Supongamos que subes la imagen a un almacenamiento y obtienes su URL
        imagen_url = request.form.get('imagen_url')
        
        # Aquí puedes agregar el código para guardar el producto en Firebase Realtime Database,
        # o en la base de datos que utilices.
        from firebase_admin import db
        ref = db.reference('catalogo')
        # Puedes usar push() para generar un nuevo ID
        nuevo_producto_ref = ref.push({
            'nombre': nombre,
            'descripcion': descripcion,
            'precio': precio,
            'categoria': categoria,
            'imagen': imagen_url
        })
        
        flash('Producto subido con éxito.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    # Si es GET, muestra el formulario de subida
    return render_template('admin/upload.html')
