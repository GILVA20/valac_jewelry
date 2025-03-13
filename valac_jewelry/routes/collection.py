from flask import Blueprint, render_template, request, current_app, flash

collection_bp = Blueprint('collection', __name__, url_prefix='/collection')

@collection_bp.route('/', methods=['GET'])
def collection_home():
    """
    Muestra la lista de productos con filtros, búsqueda, ordenamiento y paginación.
    Parámetros (query params):
      - category: filtra por tipo_producto (Anillos, Aretes, etc.)
      - type_oro: filtra por tipo_oro (10k, 14k)
      - genero: filtra por género (Hombre, Mujer, Unisex)
      - price_min, price_max: filtra por rango de precios
      - search: filtra por texto en el nombre o descripción
      - sort: ordena por 'precio_asc', 'precio_desc', 'novedades',
              'mas_vendidos', 'destacados' o 'mejor_valoracion'
      - page: para la paginación (12 productos por página)
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

    # 5. Paginación
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    limit = 12
    offset = (page - 1) * limit
    query = query.range(offset, offset + limit - 1)

    # Ejecutar la consulta
    response = query.execute()
    if response.error:
        flash("Error al cargar los productos. Intenta de nuevo.", "error")
        products = []
    else:
        products = response.data if response.data else []

    # 6. Búsqueda (post-procesado en Python)
    search = request.args.get('search', '').strip()
    if search and products:
        filtered = []
        for p in products:
            texto_completo = (p.get('nombre', '') + ' ' + p.get('descripcion', '')).lower()
            if search.lower() in texto_completo:
                filtered.append(p)
        products = filtered

    # 7. Ordenamiento adicional
    sort = request.args.get('sort', '')
    if sort == 'precio_asc':
        products.sort(key=lambda x: x.get('precio', 0))
    elif sort == 'precio_desc':
        products.sort(key=lambda x: x.get('precio', 0), reverse=True)
    elif sort == 'novedades':
        products.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort == 'mas_vendidos':
        products.sort(key=lambda x: x.get('ventas', 0), reverse=True)
    elif sort == 'destacados':
        products.sort(key=lambda x: x.get('destacado', False), reverse=True)
    elif sort == 'mejor_valoracion':
        products.sort(key=lambda x: x.get('valoracion', 0), reverse=True)

    return render_template('collection.html', products=products, page=page)
