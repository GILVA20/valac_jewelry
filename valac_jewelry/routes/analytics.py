from flask import request, current_app, flash, redirect, url_for
from flask_admin import BaseView, expose
from flask_login import current_user
from collections import Counter
from datetime import datetime, timedelta, timezone
import uuid
import requests
import logging

logger = logging.getLogger(__name__)

# ---------- Helpers de fechas ----------
def _parse_date_range(args):
    """
    Devuelve (dt_from, dt_to) en UTC (datetime con tzinfo), o (None, None).
    Prioriza: ?from=YYYY-MM-DD&to=YYYY-MM-DD  luego ?days=N
    """
    now = datetime.now(timezone.utc)
    qs_from = args.get("from")
    qs_to = args.get("to")
    qs_days = args.get("days")

    if qs_from or qs_to:
        try:
            dt_from = datetime.strptime(qs_from, "%Y-%m-%d").replace(tzinfo=timezone.utc) if qs_from else None
            # incluir fin del día si se da 'to'
            dt_to = datetime.strptime(qs_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1) if qs_to else None
            return dt_from, dt_to
        except Exception:
            logger.warning("Rango de fecha inválido: from=%s to=%s", qs_from, qs_to)

    if qs_days:
        try:
            days = int(qs_days)
            dt_from = now - timedelta(days=days)
            dt_to = now
            return dt_from, dt_to
        except Exception:
            logger.warning("Parámetro days inválido: %s", qs_days)

    # Sin filtros -> None (server usa todo)
    return None, None


class AnalyticsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/')
    def index(self):
        supabase = current_app.supabase

        # Lee rango de fechas desde querystring
        dt_from, dt_to = _parse_date_range(request.args)

        try:
            # ---------- PRODUCT VIEWS (filtrado por rango) ----------
            logger.debug("Consultando product_views con rango: from=%s to=%s", dt_from, dt_to)
            q_views = supabase.table("product_views").select("product_id, timestamp, location")
            if dt_from:
                q_views = q_views.gte("timestamp", dt_from.isoformat())
            if dt_to:
                q_views = q_views.lte("timestamp", dt_to.isoformat())
            pv_resp = q_views.execute()
            pv_rows = pv_resp.data or []

            product_ids = [row["product_id"] for row in pv_rows if row.get("product_id") is not None]
            counts = Counter(product_ids)

            # ---------- PRODUCT NAMES ----------
            product_names = {}
            try:
                # Traer TODOS para poder armar la tabla completa con 0 vistas
                names_resp = supabase.table("products").select("id, nombre").execute()
                for prod in names_resp.data or []:
                    product_names[prod["id"]] = prod["nombre"]
                all_products = list(product_names.items())  # [(id, nombre), ...]
            except Exception as e:
                logger.warning("No se pudieron traer todos los productos: %s", e)
                all_products = []

            # Top más vistos (10)
            product_views = sorted(
                [{"product_id": pid,
                  "nombre": product_names.get(pid, f"Producto ID {pid}"),
                  "views": cnt}
                 for pid, cnt in counts.items()],
                key=lambda x: x["views"],
                reverse=True
            )[:10]

            # Lista completa (todos los productos, incl. 0 vistas)
            all_product_views = []
            for pid, nombre in all_products:
                all_product_views.append({
                    "product_id": pid,
                    "nombre": nombre,
                    "views": counts.get(pid, 0)
                })
            # Orden ascendente: menos vistos primero
            all_product_views.sort(key=lambda x: x["views"])

            # ---------- NAVIGATION (filtrado por rango) ----------
            logger.debug("Consultando user_navigation con rango: from=%s to=%s", dt_from, dt_to)
            q_nav = supabase.table("user_navigation").select("path, timestamp")
            if dt_from:
                q_nav = q_nav.gte("timestamp", dt_from.isoformat())
            if dt_to:
                q_nav = q_nav.lte("timestamp", dt_to.isoformat())
            nav_resp = q_nav.execute()
            nav_rows = nav_resp.data or []
            paths = [row["path"] for row in nav_rows if row.get("path")]
            path_counts = Counter(paths)

            navigation = sorted(
                [{"path": p, "count": c} for p, c in path_counts.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10]

            # ---------- FUNNEL (por paths) ----------
            funnel_stages = [
                {'name': 'Home', 'path': '/'},
                {'name': 'Colección', 'path': '/collection'},
                {'name': 'Detalle de producto', 'path_prefix': '/producto/'},
                {'name': 'Click en comprar', 'path_prefix': '/buy-click/'},
                {'name': 'Checkout', 'path': '/checkout'},
                {'name': 'Pago exitoso', 'path': '/success'},
            ]
            funnel_data = []
            for stage in funnel_stages:
                if 'path' in stage:
                    count = path_counts.get(stage['path'], 0)
                else:
                    count = sum(1 for p in paths if p.startswith(stage['path_prefix']))
                funnel_data.append({'name': stage['name'], 'count': count})

            # ---------- KPIs ----------
            total_views = len(pv_rows)
            total_buy_clicks = sum(1 for p in paths if p.startswith("/buy-click/"))

            # Ubicaciones únicas (limpiando vacíos/None)
            locations = [row.get("location") for row in pv_rows]
            location_set = set([str(loc).strip() for loc in locations if loc and str(loc).strip().lower() != "null"])

        except Exception as e:
            logger.error("[AnalyticsAdmin] Error al consultar Supabase: %s", e)
            flash("Error al cargar analíticas. Revisa los logs.", "error")
            product_views, navigation, all_product_views = [], [], []
            total_views, total_buy_clicks, location_set = 0, 0, set()
            funnel_data = []

        # Render con mismos nombres que tu template espera
        return self.render(
            "admin/analytics.html",
            product_views=product_views,
            all_product_views=all_product_views,
            navigation=navigation,
            total_views=total_views,
            total_buy_clicks=total_buy_clicks,
            total_locations=len(location_set),
            funnel_data=funnel_data
        )

    # -------------------- Endpoints de tracking --------------------

    @expose('/track_view/<int:product_id>', methods=['POST'])
    def track_view(self, product_id):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = payload.get("session_id") or str(uuid.uuid4())
            referrer = request.headers.get("Referer")
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("product_views").insert({
                "product_id": product_id,
                "session_id": session_id,
                "referrer": referrer,
                "location": location
            }).execute()
            return "", 204
        except Exception as e:
            logger.error("Error en track_view: %s", e)
            return "", 204

    @expose('/track_navigation', methods=['POST'])
    def track_navigation(self):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = payload.get("session_id") or str(uuid.uuid4())
            path = payload.get("path") or ""
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("user_navigation").insert({
                "path": path,
                "session_id": session_id,
                "location": location
            }).execute()
            return "", 204
        except Exception as e:
            logger.error("Error en track_navigation: %s", e)
            return "", 204

    @expose('/track_buy_click/<int:product_id>', methods=['POST'])
    def track_buy_click(self, product_id):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = payload.get("session_id") or str(uuid.uuid4())
            location = self.get_location_from_ip(request.remote_addr)

            current_app.supabase.table("user_navigation").insert({
                "session_id": session_id,
                "path": f"/buy-click/{product_id}",
                "location": location
            }).execute()
            return "", 204
        except Exception as e:
            logger.error("Error en track_buy_click: %s", e)
            return "", 204

    # -------------------- Utilidades --------------------

    def get_location_from_ip(self, ip_address):
        try:
            # Evita resolver localhost/privadas
            if not ip_address or ip_address.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.")):
                return "Ubicación desconocida"
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=2.5)
            if response.status_code == 200:
                data = response.json()
                city = data.get('city') or ''
                region = data.get('region') or ''
                country = data.get('country_name') or ''
                pretty = ", ".join([v for v in [city, region, country] if v])
                return pretty or "Ubicación desconocida"
        except Exception:
            pass
        return "Ubicación desconocida"
