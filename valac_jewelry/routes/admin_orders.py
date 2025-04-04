import logging
from flask import request, redirect, url_for, flash, current_app, jsonify
from flask_admin import BaseView, expose
from flask_login import current_user

# Configuración básica de logging (si ya se configura globalmente en tu app, puedes omitir esta parte)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

ORDER_STATES = {
    'pending': ['processed', 'cancelled'],
    'processed': ['shipped', 'cancelled'],
    'shipped': ['delivered'],
    'delivered': [],
    'cancelled': []
}

class OrderService:
    def __init__(self, supabase_client):
        self.client = supabase_client

    def get_orders(self, filters=None):
        logger.debug("Obteniendo órdenes con filtros: %s", filters)
        query = self.client.table('orders').select("*")
        if filters:
            if 'estado' in filters:
                query = query.eq('estado_pago', filters['estado'])
            if 'start_date' in filters:
                query = query.gte('fecha_pedido', f"{filters['start_date']}T00:00:00")
            if 'end_date' in filters:
                query = query.lte('fecha_pedido', f"{filters['end_date']}T23:59:59")
        result = query.order("fecha_pedido", desc=True).execute()
        logger.debug("Respuesta de supabase: %s", result)
        return result

    def get_stats(self, orders):
        stats = {
            "total": len(orders),
            "pending": sum(1 for o in orders if o['estado_pago'] == 'pending'),
            "processed": sum(1 for o in orders if o['estado_pago'] == 'processed'),
            "shipped": sum(1 for o in orders if o['estado_pago'] == 'shipped'),
            "delivered": sum(1 for o in orders if o['estado_pago'] == 'delivered'),
            "completed": sum(1 for o in orders if o['estado_pago'] == 'delivered'),
            "cancelled": sum(1 for o in orders if o['estado_pago'] == 'cancelled')
        }
        logger.debug("Estadísticas calculadas: %s", stats)
        return stats

    def update_order_state(self, order_id, new_state):
        logger.debug("Actualizando orden %s a estado %s", order_id, new_state)
        return self.client.table("orders").update({"estado_pago": new_state}).eq("id", order_id).execute()

class OrderAdminView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/')
    def index(self):
        service = OrderService(self.admin.app.supabase)
        stats = service.get_stats([])  # KPIs iniciales vacíos
        logger.debug("Mostrando vista de órdenes con estadísticas iniciales: %s", stats)
        return self.render('admin/orders_list.html', stats=stats)

    @expose('/transition/<int:order_id>/<string:action>', methods=['POST'])
    def transition(self, order_id, action):
        current_state = request.form.get("current_state")
        if not current_state or action not in ORDER_STATES.get(current_state, []):
            flash("Transición no permitida.", "error")
            logger.warning("Transición no permitida: current_state=%s, action=%s", current_state, action)
            return redirect(url_for('.index'))

        service = OrderService(self.admin.app.supabase)
        result = service.update_order_state(order_id, action)
        if not result.data:
            flash("No se pudo actualizar el estado de la orden.", "error")
            logger.error("Error al actualizar la orden %s con acción %s", order_id, action)
        else:
            flash("Estado de la orden actualizado exitosamente.", "success")
            logger.debug("Orden %s actualizada a %s exitosamente.", order_id, action)
        return redirect(url_for('.index'))

    @expose('/json')
    def json(self):
        service = OrderService(self.admin.app.supabase)
        try:
            filters = {
                'start_date': request.args.get('start_date'),
                'end_date': request.args.get('end_date'),
                'estado': request.args.get('estado')
            }
            filters = {k: v for k, v in filters.items() if v}
            logger.debug("Filtros recibidos para la consulta de órdenes: %s", filters)
            response = service.get_orders(filters)
            orders = response.data or []

            for order in orders:
                order['cliente'] = {
                    "id": order.get("cliente_id"),
                    "nombre": order.get("nombre", "")
                }

            stats = service.get_stats(orders)
            logger.debug("Enviando JSON con %d órdenes", len(orders))
            return jsonify({
                "data": orders,
                "stats": stats,
                "recordsTotal": len(orders),
                "recordsFiltered": len(orders),
                "draw": 1
            })
        except Exception as e:
            logger.error("Error en /admin/orders/json: %s", e)
            return jsonify({"error": str(e)}), 500
