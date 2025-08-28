from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for, flash
from flask_admin import BaseView, expose  # tipo BaseView, mismo patrón que admin_orders
from flask_login import current_user

LOCAL_TZS = {
    "America/Monterrey": "Monterrey",
    "America/Mexico_City": "CDMX",
}

def _round2(x: Any) -> Decimal:
    return Decimal(str(x or "0")).quantize(Decimal("0.01"))

class CouponsAdminView(BaseView):
    """
    Admin CRUD de cupones usando Supabase client (igual approach que otros Admin de tu app).
    """
    def is_accessible(self) -> bool:
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a Cupones.", "error")
        return redirect(url_for("auth.login", next=request.url))

    @property
    def sb(self):
        return self.admin.app.supabase

    # -------------------------------
    # LISTA
    # -------------------------------
    @expose("/", methods=["GET"])
    def index(self):
        res = self.sb.table("coupons").select("*").order("created_at", desc=True).execute()
        coupons: List[Dict[str, Any]] = res.data or []
        return self.render("admin/coupons_list.html", coupons=coupons, tz_labels=LOCAL_TZS)

    # -------------------------------
    # NUEVO / EDITAR
    # -------------------------------
    @expose("/new", methods=["GET", "POST"])
    def new(self):
        if request.method == "POST":
            return self._upsert()
        return self.render("admin/coupons_form.html", coupon=None, tz_labels=LOCAL_TZS)

    @expose("/edit/<int:coupon_id>", methods=["GET", "POST"])
    def edit(self, coupon_id: int):
        if request.method == "POST":
            return self._upsert(coupon_id)
        res = self.sb.table("coupons").select("*").eq("id", coupon_id).single().execute()
        if not res.data:
            flash("Cupón no encontrado.", "error")
            return redirect(url_for(".index"))
        return self.render("admin/coupons_form.html", coupon=res.data, tz_labels=LOCAL_TZS)

    def _upsert(self, coupon_id: Optional[int] = None):
        f = request.form
        code = (f.get("code") or "").strip().upper()
        ctype = f.get("type") or "percent"
        value = _round2(f.get("value"))
        tz = f.get("timezone") or "America/Monterrey"
        cap_mode = f.get("cap_mode") or "both"
        active = f.get("active") == "on"
        starts_at_local = f.get("starts_at")  # 'YYYY-MM-DDTHH:mm'
        ends_at_local = f.get("ends_at")
        min_order_amount = f.get("min_order_amount") or None
        max_uses = f.get("max_uses") or None
        max_uses_per_user = f.get("max_uses_per_user") or None
        cap_amount = f.get("cap_amount") or None
        cap_percent = f.get("cap_percent") or None
        cap_amount_msi = f.get("cap_amount_msi") or None
        cap_percent_msi = f.get("cap_percent_msi") or None
        notes = f.get("notes") or None

        # Parsear fechas locales -> UTC
        tzinfo = pytz.timezone(tz)
        try:
            starts_utc = tzinfo.localize(datetime.fromisoformat(starts_at_local)).astimezone(pytz.UTC)
            ends_utc = tzinfo.localize(datetime.fromisoformat(ends_at_local)).astimezone(pytz.UTC)
        except Exception:
            flash("Fechas inválidas. Usa el selector de fecha/hora.", "error")
            return redirect(request.referrer or url_for(".index"))
        if ends_utc <= starts_utc:
            flash("La fecha de fin debe ser posterior al inicio.", "error")
            return redirect(request.referrer or url_for(".index"))

        payload: Dict[str, Any] = {
            "code": code,
            "type": ctype,
            "value": float(value),
            "starts_at": starts_utc.isoformat(),
            "ends_at": ends_utc.isoformat(),
            "timezone": tz,
            "active": active,
            "cap_mode": cap_mode,
        }
        if min_order_amount:   payload["min_order_amount"] = float(_round2(min_order_amount))
        if max_uses:           payload["max_uses"] = int(max_uses)
        if max_uses_per_user:  payload["max_uses_per_user"] = int(max_uses_per_user)
        if cap_amount:         payload["cap_amount"] = float(_round2(cap_amount))
        if cap_percent:        payload["cap_percent"] = float(_round2(cap_percent))
        if cap_amount_msi:     payload["cap_amount_msi"] = float(_round2(cap_amount_msi))
        if cap_percent_msi:    payload["cap_percent_msi"] = float(_round2(cap_percent_msi))
        if notes:              payload["notes"] = notes.strip()

        if coupon_id:
            res = self.sb.table("coupons").update(payload, returning="representation").eq("id", coupon_id).execute()
            ok = bool(res.data)
            msg = "Cupón actualizado" if ok else "No se pudo actualizar el cupón"
        else:
            res = self.sb.table("coupons").insert(payload).execute()
            ok = bool(res.data)
            msg = "Cupón creado" if ok else "No se pudo crear el cupón"

        flash(msg, "success" if ok else "error")
        return redirect(url_for(".index"))

    # -------------------------------
    # Activar / Desactivar rápido
    # -------------------------------
    @expose("/toggle/<int:coupon_id>", methods=["POST"])
    def toggle(self, coupon_id: int):
        row = self.sb.table("coupons").select("active").eq("id", coupon_id).single().execute()
        if not row.data:
            flash("Cupón no encontrado.", "error")
            return redirect(url_for(".index"))
        new_val = not bool(row.data["active"])
        self.sb.table("coupons").update({"active": new_val}, returning="representation").eq("id", coupon_id).execute()
        flash("Estado actualizado.", "success")
        return redirect(url_for(".index"))
