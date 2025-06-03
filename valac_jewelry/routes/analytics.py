from flask import request, current_app, flash, redirect, url_for
from flask_admin import BaseView, expose
from flask_login import current_user
from collections import Counter
import hashlib
import uuid
import requests
import logging

logger = logging.getLogger(__name__)

class AnalyticsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/')
    def index(self):
        supabase = current_app.supabase

        try:
            logger.debug("Consultando vistas de productos")
            product_views_raw = supabase.table("product_views").select("product_id").execute()
            product_ids = [entry["product_id"] for entry in (product_views_raw.data or [])]
            counts = Counter(product_ids)

            logger.debug("Consultando nombres de productos")
            product_names = {}
            if product_ids:
                names_resp = supabase.table("products").select("id, nombre").in_("id", product_ids).execute()
                for prod in names_resp.data or []:
                    product_names[prod["id"]] = prod["nombre"]

            product_views = sorted(
                [{"product_id": pid, "nombre": product_names.get(pid, f"Producto ID {pid}"), "views": count}
                 for pid, count in counts.items()],
                key=lambda x: x["views"],
                reverse=True
            )[:10]

            logger.debug("Consultando navegación de usuarios")
            navigation_raw = supabase.table("user_navigation").select("path").execute()
            paths = [entry["path"] for entry in (navigation_raw.data or [])]
            path_counts = Counter(paths)
            navigation = sorted(
                [{"path": path, "count": count} for path, count in path_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10]

            logger.debug("Calculando embudo de conversión")
            funnel_stages = [
                {'name': 'Home', 'path': '/'},
                {'name': 'Colección', 'path': '/collection'},
                {'name': 'Detalle de producto', 'path_prefix': '/producto/'},
                {'name': 'Click en comprar', 'path_prefix': '/buy-click/'},
                {'name': 'Checkout', 'path': '/checkout'},
                {'name': 'Pago exitoso', 'path': '/success'}
            ]
            funnel_data = []
            for stage in funnel_stages:
                if 'path' in stage:
                    count = path_counts.get(stage['path'], 0)
                else:
                    count = sum(1 for p in paths if p.startswith(stage['path_prefix']))
                funnel_data.append({'name': stage['name'], 'count': count})

            logger.debug("Calculando KPIs")
            total_views = len(product_ids)
            total_buy_clicks = len([
                p for p in paths if p.startswith("/buy-click/")
            ])
            unique_locations = supabase.table("product_views").select("location").execute()
            location_set = set([entry["location"] for entry in (unique_locations.data or [])])

        except Exception as e:
            logger.error("[AnalyticsAdmin] Error al consultar Supabase: %s", e)
            flash("Error al cargar analíticas. Revisa los logs.", "error")
            product_views, navigation = [], []
            total_views, total_buy_clicks, location_set = 0, 0, set()

        return self.render(
            "admin/analytics.html",
            product_views=product_views,
            navigation=navigation,
            total_views=total_views,
            total_buy_clicks=total_buy_clicks,
            total_locations=len(location_set),
            funnel_data=funnel_data
        )

    @expose('/track_view/<int:product_id>', methods=['POST'])
    def track_view(self, product_id):
        try:
            logger.debug("Registrando vista para el producto %s", product_id)
            session_id = request.json.get("session_id")
            referrer = request.headers.get("Referer")
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("product_views").insert({
                "product_id": product_id,
                "session_id": session_id,
                "referrer": referrer,
                "location": location
            }).execute()
        except Exception as e:
            logger.error("Error en track_view: %s", e)
        return "", 204

    @expose('/track_navigation', methods=['POST'])
    def track_navigation(self):
        try:
            logger.debug("Registrando navegación de usuario")
            data = request.json
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("user_navigation").insert({
                "path": data.get("path"),
                "session_id": data.get("session_id"),
                "location": location
            }).execute()
        except Exception as e:
            logger.error("Error en track_navigation: %s", e)
        return "", 204

    @expose('/track_buy_click/<int:product_id>', methods=['POST'])
    def track_buy_click(self, product_id):
        try:
            logger.debug("Registrando clic en comprar para el producto %s", product_id)
            session_id = request.json.get("session_id")
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("user_navigation").insert({
                "session_id": session_id,
                "path": f"/buy-click/{product_id}",
                "location": location
            }).execute()
        except Exception as e:
            logger.error("Error en track_buy_click: %s", e)
        return "", 204

    def get_location_from_ip(self, ip_address):
        try:
            response = requests.get(f'https://ipapi.co/{ip_address}/json/')
            if response.status_code == 200:
                data = response.json()
                return f"{data.get('city')}, {data.get('region')}, {data.get('country_name')}"
        except Exception:
            pass
        return "Ubicación desconocida"
