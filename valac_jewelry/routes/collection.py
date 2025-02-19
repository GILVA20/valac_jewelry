## valac_jewelry/routes/collection.py
#from flask import Blueprint, render_template, current_app
#
#collections_bp = Blueprint('collection', __name__)
#
#@collections_bp.route('/')
#def collection_home():
#    supabase = current_app.supabase
#    response = supabase.table("products").select("*").execute()
#    # Si response.data existe, úsalo; de lo contrario, asigna una lista vacía
#    products = response.data if response.data else []
#    return render_template('collection.html', products=products)
#
#@collections_bp.route('/')
#def list_products():
#    supabase = current_app.supabase
#    response = supabase.table("products").select("*").execute()
#    if not response.data:
#        current_app.logger.error("Error al obtener productos: " + str(response))
#        products = []
#    else:
#        products = response.data
#        current_app.logger.info(f"Productos obtenidos: {products}")
#    return render_template('collection.html', products=products)
# valac_jewelry/routes/collection.py
from flask import Blueprint, render_template, request, current_app

collection_bp = Blueprint('collection', __name__, url_prefix='/collection')

@collection_bp.route('/', methods=['GET'])
def collection_home():
    """
    Muestra la lista de productos con filtros, búsqueda y ordenamiento.
    Parámetros posibles (query params):
      - category: filtra por tipo_producto (Anillos, Aretes, etc.)
      - type_oro: filtra por tipo_oro (10k, 14k)
      - genero: filtra por género (Hombre, Mujer, Unisex)
      - price_min, price_max: filtra por rango de precios
      - search: filtra por texto en el nombre o descripción
      - sort: ordena por 'precio_asc', 'precio_desc', 'novedades'
    """
    supabase = current_app.supabase
    
    # Iniciar query base
    query = supabase.table('products').select('*')
    
    # 1. Filtro por categoría (tipo_producto)
    category = request.args.get('category', '').strip()
    if category:
        query = query.eq('tipo_producto', category)
    
    # 2. Filtro por tipo de oro
    type_oro = request.args.get('type_oro', '').strip()
    if type_oro:
        query = query.eq('tipo_oro', type_oro)
    
    # 3. Filtro por género
    genero = request.args.get('genero', '').strip()
    if genero:
        query = query.eq('genero', genero)
    
    # 4. Filtro por rango de precios
    price_min = request.args.get('price_min', '').strip()
    price_max = request.args.get('price_max', '').strip()
    if price_min.isdigit():
        query = query.gte('precio', int(price_min))
    if price_max.isdigit():
        query = query.lte('precio', int(price_max))
    
    # 5. Búsqueda por texto
    search = request.args.get('search', '').strip()
    if search:
        # Supabase no tiene "full text search" por defecto en la API REST,
        # pero podemos simular un "ILIKE" si la extensión lo permite.
        # Si no, lo más sencillo es filtrar en Python (menos eficiente).
        # Ejemplo de filtro simple en Python (post-procesado):
        # query = query.ilike('nombre', f'%{search}%') -> no siempre disponible.
        pass
    
    # Ejecutamos la query y obtenemos resultados
    response = query.execute()
    products = response.data if response.data else []
    
    # 5. Búsqueda manual en Python (opcional, si no tienes ilike en Supabase)
    if search and products:
        filtered = []
        for p in products:
            # Convertir a minúsculas para búsqueda simple
            texto_completo = (p['nombre'] + ' ' + p['descripcion']).lower()
            if search.lower() in texto_completo:
                filtered.append(p)
        products = filtered
    
    # 6. Ordenamiento
    sort = request.args.get('sort', '')
    if sort == 'precio_asc':
        products.sort(key=lambda x: x['precio'])
    elif sort == 'precio_desc':
        products.sort(key=lambda x: x['precio'], reverse=True)
    elif sort == 'novedades':
        # Suponiendo que 'created_at' indica novedad
        products.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('collection.html', products=products)
