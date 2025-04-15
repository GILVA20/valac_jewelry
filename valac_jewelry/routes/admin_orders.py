import logging, json, datetime
from flask import request, redirect, url_for, flash, current_app, jsonify
from flask_admin import BaseView, expose
from flask_login import current_user

logger = logging.getLogger(__name__)

# Flujos de estados para pago y envío
PAYMENT_STATES = {
    'pending': ['paid', 'refunded'],
    'paid': [],
    'refunded': []
}

SHIPPING_STATES = {
    'unshipped': ['processing'],
    'processing': ['shipped', 'cancelled'],
    'shipped': ['delivered'],
    'delivered': [],
    'cancelled': []
}

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
        try:
            logger.debug("Obteniendo órdenes con filtros: %s", filters)
            query = self.client.table('orders').select("*")
            if filters:
                if 'estado_pago' in filters:
                    query = query.eq('estado_pago', filters['estado_pago'])
                if 'estado_envio' in filters:
                    query = query.eq('estado_envio', filters['estado_envio'])
                if 'start_date' in filters:
                    query = query.gte('fecha_pedido', f"{filters['start_date']}T00:00:00")
                if 'end_date' in filters:
                    query = query.lte('fecha_pedido', f"{filters['end_date']}T23:59:59")
            result = query.order("fecha_pedido", desc=True).execute()
            logger.debug("Respuesta de Supabase: %s", result)
            return result
        except Exception as e:
            logger.error("Error obteniendo órdenes: %s", e)
            return None

    def get_order_detail(self, order_id):
        try:
            logger.debug("Obteniendo detalle de orden id: %s", order_id)
            result = self.client.table('orders').select(
                "*,user_id(nombre,email),dirección_envío,ciudad,status_history"
            ).eq("id", order_id).execute()

            if result.data:
                # Combine address fields manually
                order = result.data[0]
                order['direccion_completa'] = f"{order.get('direccion_envio', '')}, {order.get('ciudad', '')}"
                logger.debug("Detalle de orden obtenido: %s", order)
                return order
            else:
                logger.error("Orden con id %s no encontrada", order_id)
                return None
        except Exception as e:
            logger.error("Error obteniendo detalle de orden %s: %s", order_id, e)
            return None

    def get_stats(self, orders):
        """
        Calcula estadísticas clave a partir de la lista de órdenes.
        Devuelve un diccionario con:
          {
            'total': int,
            'pending_payment': int,
            'paid': int,
            'refunded': int,
            'unshipped': int,
            'processing': int,
            'shipped': int,
            'delivered': int
          }
        """
        stats = {
            'total': 0,
            'pending_payment': 0,
            'paid': 0,
            'refunded': 0,
            'unshipped': 0,
            'processing': 0,
            'shipped': 0,
            'delivered': 0
        }
        if orders is None:
            return stats
        for order in orders:
            stats['total'] += 1
            # Estadísticas de pago
            payment = (order.get('estado_pago') or '').lower()
            if payment == 'pending':
                stats['pending_payment'] += 1
            elif payment == 'paid':
                stats['paid'] += 1
            elif payment == 'refunded':
                stats['refunded'] += 1
            # Estadísticas de envío
            shipping = (order.get('estado_envio') or 'unshipped').lower()
            if shipping == 'unshipped':
                stats['unshipped'] += 1
            elif shipping == 'processing':
                stats['processing'] += 1
            elif shipping == 'shipped':
                stats['shipped'] += 1
            elif shipping == 'delivered':
                stats['delivered'] += 1
        return stats

    def update_order_detail(self, order_id, update_data):
        """
        Actualiza los detalles de una orden en la base de datos.
        """
        try:
            logger.debug("Actualizando orden %s con data: %s", order_id, update_data)
            result = self.client.table('orders').update(update_data).eq('id', order_id).execute()
            logger.debug("Resultado actualización: %s", result)
            return result
        except Exception as e:
            logger.error("Error actualizando la orden %s: %s", order_id, e)
            return None

    def update_order_state(self, order_id, new_state):
        """
        Actualiza el estado principal de la orden validando la transición en base a ORDER_STATES.
        """
        try:
            logger.debug("Actualizando estado de orden %s a %s", order_id, new_state)
            result = self.client.table('orders').update({'estado': new_state}).eq('id', order_id).execute()
            logger.debug("Resultado actualización de estado: %s", result)
            return result
        except Exception as e:
            logger.error("Error actualizando estado de la orden %s: %s", order_id, e)
            return None

    def update_order_payment(self, order_id, current_order):
        """
        Actualiza el estado de pago de la orden validando la transición usando PAYMENT_STATES.
        """
        new_payment = request.form.get("estado_pago", "").strip().lower()
        current_payment = (current_order.get("estado_pago") or "").strip().lower()
        if new_payment and new_payment != current_payment:
            allowed_payments = PAYMENT_STATES.get(current_payment, [])
            if new_payment not in allowed_payments:
                flash(f"Transición de pago no permitida: de '{current_payment}' a '{new_payment}'.", "error")
                return None
            update_data = {"estado_pago": new_payment}
            return self.update_order_detail(order_id, update_data)
        return None  # No hubo cambio en pago

    def update_order_shipping(self, order_id, current_order):
        """
        Actualiza la información de envío:
          - Valida la transición usando SHIPPING_STATES.
          - Actualiza campos: estado_envio, guia_envio, fecha_envio_cliente.
          - Registra en status_history la actualización.
        """
        new_shipping = request.form.get("estado_envio", "").strip().lower()
        guia_envio = request.form.get("guia_envio", "").strip()
        fecha_envio_cliente = request.form.get("fecha_envio_cliente", "").strip()
        new_shipping_address = request.form.get("shipping_address")
        new_shipping_method = request.form.get("shipping_method")
        new_tracking_number = request.form.get("tracking_number")
        
        current_shipping = (current_order.get("estado_envio") or "unshipped").strip().lower()
        if new_shipping and new_shipping != current_shipping:
            allowed = SHIPPING_STATES.get(current_shipping, [])
            if new_shipping not in allowed:
                flash(f"Transición de envío no permitida: de '{current_shipping}' a '{new_shipping}'.", "error")
                return None
        
        history = current_order.get("status_history")
        if not history:
            history = []
        else:
            if isinstance(history, str):
                try:
                    history = json.loads(history)
                except Exception as e:
                    logger.error("Error parseando status_history: %s", e)
                    history = []
        
        history_entry = {
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "user": current_user.email if hasattr(current_user, "email") else "admin",
            "estado_envio": new_shipping,
            "guia_envio": guia_envio,
            "fecha_envio_cliente": fecha_envio_cliente
        }
        if new_shipping_address:
            history_entry["shipping_address"] = new_shipping_address
        if new_shipping_method:
            history_entry["shipping_method"] = new_shipping_method
        if new_tracking_number:
            history_entry["tracking_number"] = new_tracking_number
        history.append(history_entry)
        
        update_data = {
            "estado_envio": new_shipping,
            "guia_envio": guia_envio,
            "fecha_envio_cliente": fecha_envio_cliente,
            "status_history": json.dumps(history)
        }
        if new_shipping_address:
            update_data["shipping_address"] = new_shipping_address
        if new_shipping_method:
            update_data["shipping_method"] = new_shipping_method
        if new_tracking_number:
            update_data["tracking_number"] = new_tracking_number
        
        return self.update_order_detail(order_id, update_data)

class OrderAdminView(BaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/')
    def index(self):
        # Considerar mover esta función a un proceso asíncrono o eliminarla de la vista principal
        # self.update_all_direccion_completa()
        service = OrderService(self.admin.app.supabase)
        orders_result = service.get_orders()
        orders = orders_result.data if orders_result and orders_result.data else []
        stats = service.get_stats(orders)
        logger.debug("Mostrando vista de órdenes con estadísticas: %s", stats)
        return self.render('admin/orders_list.html', stats=stats)


    def update_all_direccion_completa(self):
        """
        Recorre todas las órdenes y actualiza 'direccion_completa' concatenando
        direccion_envio, colonia, ciudad, codigo_postal y estado_geografico.
        """
        service = OrderService(self.admin.app.supabase)
        result = service.get_orders()
        if not result or not result.data:
            logger.debug("No se encontraron órdenes para actualizar direccion_completa.")
            return
        for order in result.data:
            direccion = order.get("direccion_envio") or ""
            colonia = order.get("colonia") or ""
            ciudad = order.get("ciudad") or ""
            codigo_postal = order.get("codigo_postal") or ""
            estado_geografico = order.get("estado_geografico") or ""
            complete_address = ", ".join(filter(None, [direccion, colonia, ciudad, codigo_postal, estado_geografico]))
            if order.get("direccion_completa") != complete_address:
                update_data = {"direccion_completa": complete_address}
                update_result = service.update_order_detail(order["id"], update_data)
                if update_result and update_result.data:
                    logger.debug(f"Order {order['id']} actualizada: direccion_completa = {complete_address}")
                else:
                    logger.error(f"Fallo al actualizar la orden {order['id']}")

    @expose('/transition/<int:order_id>/<string:action>', methods=['POST'])
    def transition(self, order_id, action):
        current_state = request.form.get("current_state")
        if not current_state or action not in ORDER_STATES.get(current_state, []):
            flash("Transición no permitida.", "error")
            logger.warning("Transición no permitida: current_state=%s, action=%s", current_state, action)
            return redirect(url_for('.index'))

        service = OrderService(self.admin.app.supabase)
        result = service.update_order_state(order_id, action)
        if not result or not result.data:
            flash("No se pudo actualizar el estado de la orden.", "error")
            logger.error("Error al actualizar la orden %s con acción %s", order_id, action)
        else:
            flash("Estado de la orden actualizado exitosamente.", "success")
            logger.debug("Orden %s actualizada a %s exitosamente.", order_id, action)
        return redirect(url_for('.index'))

    @expose('/<int:order_id>', methods=['GET', 'POST'])
    def detail(self, order_id, **kwargs):
        logger.debug("Entrando al endpoint detail con order_id: %s", order_id)
        service = OrderService(self.admin.app.supabase)
        
        if request.method == 'POST':
            logger.debug("Método POST recibido para order_id: %s", order_id)
            current_order = service.get_order_detail(order_id)
            logger.debug("Orden actual recuperada: %s", current_order)
            
            if not current_order:
                flash("Orden no encontrada.", "error")
                logger.error("Orden no encontrada para order_id: %s", order_id)
                return redirect(url_for('.index'))
            
            result_payment = service.update_order_payment(order_id, current_order)
            result_shipping = service.update_order_shipping(order_id, current_order)
            logger.debug("Resultado de actualización - Pago: %s, Envío: %s", result_payment, result_shipping)
            
            if ((result_payment is None or (result_payment and result_payment.data)) and 
                (result_shipping is None or (result_shipping and result_shipping.data))):
                flash("Detalles de la orden actualizados exitosamente.", "success")
                logger.debug("Orden actualizada correctamente para order_id: %s", order_id)
            else:
                flash("No se pudo actualizar la orden.", "error")
                logger.error("Error al actualizar la orden para order_id: %s", order_id)
            return redirect(url_for('.detail', order_id=order_id))
        else:
            logger.debug("Método GET recibido para order_id: %s", order_id)
            order = service.get_order_detail(order_id)
            logger.debug("Detalle de la orden obtenido: %s", order)
            
            if not order:
                flash("Orden no encontrada.", "error")
                logger.error("Orden no encontrada en GET para order_id: %s", order_id)
                return redirect(url_for('.index'))
            
            return self.render('admin/admin_order_detail.html',
                            order=order,
                            PAYMENT_STATES=PAYMENT_STATES,
                            SHIPPING_STATES=SHIPPING_STATES)

    def update_shipping_info(self, order_id, current_order):
        """
        Función para actualizar la información de envío:
        - Valida la transición de estado usando SHIPPING_STATES.
        - Actualiza campos como estado_envio, guia_envio, fecha_envio_cliente.
        - Registra en status_history la actualización (incluyendo opcionalmente
          shipping_address, shipping_method y tracking_number si se envían).
        """
        # (Esta función se mantiene para compatibilidad, pero su funcionalidad queda reemplazada
        # por update_order_shipping. Se recomienda borrar esta función en futuras refactorizaciones.)
        new_shipping = request.form.get("estado_envio", "").strip().lower()
        guia_envio = request.form.get("guia_envio", "").strip()
        fecha_envio_cliente = request.form.get("fecha_envio_cliente", "").strip()
        new_shipping_address = request.form.get("shipping_address")
        new_shipping_method = request.form.get("shipping_method")
        new_tracking_number = request.form.get("tracking_number")
        
        current_shipping = (current_order.get("estado_envio") or "unshipped").strip().lower()
        if new_shipping and new_shipping != current_shipping:
            allowed = SHIPPING_STATES.get(current_shipping, [])
            if new_shipping not in allowed:
                flash(f"Transición de envío no permitida: de '{current_shipping}' a '{new_shipping}'.", "error")
                return None
        
        history = current_order.get("status_history")
        if not history:
            history = []
        else:
            if isinstance(history, str):
                try:
                    history = json.loads(history)
                except Exception as e:
                    logger.error("Error parseando status_history: %s", e)
                    history = []
        
        history_entry = {
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "user": current_user.email if hasattr(current_user, "email") else "admin",
            "estado_envio": new_shipping,
            "guia_envio": guia_envio,
            "fecha_envio_cliente": fecha_envio_cliente
        }
        if new_shipping_address:
            history_entry["shipping_address"] = new_shipping_address
        if new_shipping_method:
            history_entry["shipping_method"] = new_shipping_method
        if new_tracking_number:
            history_entry["tracking_number"] = new_tracking_number
        history.append(history_entry)
        
        update_data = {
            "estado_envio": new_shipping,
            "guia_envio": guia_envio,
            "fecha_envio_cliente": fecha_envio_cliente,
            "status_history": json.dumps(history)
        }
        if new_shipping_address:
            update_data["shipping_address"] = new_shipping_address
        if new_shipping_method:
            update_data["shipping_method"] = new_shipping_method
        if new_tracking_number:
            update_data["tracking_number"] = new_tracking_number
        
        service = OrderService(self.admin.app.supabase)
        result = service.update_order_detail(order_id, update_data)
        return result

    @expose('/json')
    def json(self):
        service = OrderService(self.admin.app.supabase)
        try:
            filters = {
                'start_date': request.args.get('start_date'),
                'end_date': request.args.get('end_date'),
                'estado_pago': request.args.get('estado'),
                'estado_envio': request.args.get('estado_envio')
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
