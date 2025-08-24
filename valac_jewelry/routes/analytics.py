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
    Si viene 'to', se interpreta como fin del día (to + 1 día) para inclusividad.
    """
    now = datetime.now(timezone.utc)
    qs_from = args.get("from")
    qs_to = args.get("to")
    qs_days = args.get("days")

    if qs_from or qs_to:
        try:
            dt_from = datetime.strptime(qs_from, "%Y-%m-%d").replace(tzinfo=timezone.utc) if qs_from else None
            dt_to = (
                datetime.strptime(qs_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
                if qs_to else None
            )
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


# ---------- Helpers de ubicación ----------
def _extract_city_region(loc):
    """
    Devuelve (city, region, country) desde el campo 'location' que puede ser:
    - dict (nuevo formato JSON)
    - string "Ciudad, Estado, País" (legado)
    - None
    """
    if not loc:
        return None, None, None

    if isinstance(loc, dict):
        return (
            (loc.get("city") or None),
            (loc.get("region") or None),
            (loc.get("country") or loc.get("country_name") or None),
        )

    if isinstance(loc, str):
        parts = [p.strip() for p in loc.split(",")]
        city = parts[0] if len(parts) > 0 else None
        region = parts[1] if len(parts) > 1 else None
        country = parts[2] if len(parts) > 2 else None
        return city, region, country

    return None, None, None


def _get_client_ip(req):
    """
    Obtén la IP del cliente respetando proxies/reverse-proxies.
    """
    xff = req.headers.get("X-Forwarded-For", "")
    if xff:
        # XFF puede traer "ip1, ip2, ip3", nos quedamos con la primera pública
        first = xff.split(",")[0].strip()
        if first:
            return first
    return req.remote_addr


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
                [
                    {
                        "product_id": pid,
                        "nombre": product_names.get(pid, f"Producto ID {pid}"),
                        "views": cnt,
                    }
                    for pid, cnt in counts.items()
                ],
                key=lambda x: x["views"],
                reverse=True,
            )[:10]

            # Lista completa (todos los productos, incl. 0 vistas)
            all_product_views = [
                {
                    "product_id": pid,
                    "nombre": nombre,
                    "views": counts.get(pid, 0),
                }
                for pid, nombre in all_products
            ]
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
                reverse=True,
            )[:10]

            # ---------- FUNNEL (por paths) ----------
            funnel_stages = [
                {"name": "Home", "path": "/"},
                {"name": "Colección", "path": "/collection"},
                {"name": "Detalle de producto", "path_prefix": "/producto/"},
                {"name": "Click en comprar", "path_prefix": "/buy-click/"},
                {"name": "Checkout", "path": "/checkout"},
                {"name": "Pago exitoso", "path": "/success"},
            ]
            funnel_data = []
            for stage in funnel_stages:
                if "path" in stage:
                    count = path_counts.get(stage["path"], 0)
                else:
                    pref = stage["path_prefix"]
                    count = sum(1 for p in paths if p and p.startswith(pref))
                funnel_data.append({"name": stage["name"], "count": count})

            # ---------- KPIs ----------
            total_views = len(pv_rows)
            total_buy_clicks = sum(1 for p in paths if p and p.startswith("/buy-click/"))

            # ---------- Ubicaciones (Top regiones/ciudades) ----------
            cities_counter = Counter()
            regions_counter = Counter()
            location_set = set()

            for row in pv_rows:
                city, region, country = _extract_city_region(row.get("location"))
                if city:
                    cities_counter[city] += 1
                if region:
                    regions_counter[region] += 1
                key = (city or "", region or "", country or "")
                if any(key):
                    location_set.add(key)

            top_cities = [{"city": c, "count": n} for c, n in cities_counter.most_common(10)]
            top_regions = [{"region": r, "count": n} for r, n in regions_counter.most_common(10)]

        except Exception as e:
            logger.error("[AnalyticsAdmin] Error al consultar Supabase: %s", e)
            flash("Error al cargar analíticas. Revisa los logs.", "error")
            product_views, navigation, all_product_views = [], [], []
            total_views, total_buy_clicks = 0, 0
            funnel_data = []
            top_cities, top_regions = [], []
            location_set = set()

        # Render con los nombres que el template espera + nuevas tablas de ubicación
        return self.render(
            "admin/analytics.html",
            product_views=product_views,
            all_product_views=all_product_views,
            navigation=navigation,
            total_views=total_views,
            total_buy_clicks=total_buy_clicks,
            total_locations=len(location_set),
            funnel_data=funnel_data,
            top_cities=top_cities,
            top_regions=top_regions,
        )

    # -------------------- Endpoints de tracking --------------------

    @expose('/track_view/<int:product_id>', methods=['POST'])
    def track_view(self, product_id):
        try:
            payload = request.get_json(silent=True) or {}
            session_id = payload.get("session_id") or str(uuid.uuid4())
            referrer = request.headers.get("Referer")
            ip = _get_client_ip(request)
            location = self.get_location_from_ip(ip)

            current_app.supabase.table("product_views").insert({
                "product_id": product_id,
                "session_id": session_id,
                "referrer": referrer,
                "location": location,   # <-- JSON estructurado
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
            ip = _get_client_ip(request)
            location = self.get_location_from_ip(ip)

            current_app.supabase.table("user_navigation").insert({
                "path": path,
                "session_id": session_id,
                "location": location,   # <-- JSON estructurado
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
            ip = _get_client_ip(request)
            location = self.get_location_from_ip(ip)

            current_app.supabase.table("user_navigation").insert({
                "session_id": session_id,
                "path": f"/buy-click/{product_id}",
                "location": location,   # <-- JSON estructurado
            }).execute()
            return "", 204
        except Exception as e:
            logger.error("Error en track_buy_click: %s", e)
            return "", 204

    # -------------------- Utilidades --------------------

    def get_location_from_ip(self, ip_address):
        """
        Devuelve un dict JSON listo para guardar en jsonb:
        {
          ip, city, region, region_code, country, country_code, postal,
          latitude, longitude, timezone
        }
        Backwards-safe: si falla, devuelve city/region/country = None.
        """
        try:
            # Evita resolver localhost/privadas
            private_prefixes = ("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.")
            if not ip_address or ip_address.startswith(private_prefixes):
                return {"ip": ip_address, "city": None, "region": None, "country": None}

            resp = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=2.5)
            if resp.status_code == 200:
                d = resp.json() or {}
                return {
                    "ip": ip_address,
                    "city": d.get("city"),
                    "region": d.get("region"),
                    "region_code": d.get("region_code"),
                    "country": d.get("country_name"),
                    "country_code": d.get("country"),
                    "postal": d.get("postal"),
                    "latitude": d.get("latitude"),
                    "longitude": d.get("longitude"),
                    "timezone": d.get("timezone"),
                }
        except Exception:
            pass

        return {"ip": ip_address, "city": None, "region": None, "country": None}
