
from __future__ import annotations
from decimal import Decimal
from flask import Blueprint, current_app, request, jsonify
from flask_login import current_user
from datetime import datetime
import pytz

from ..services.discounts_service import apply_coupon, is_coupon_active, _round2
from ..services.limits_service import can_use_coupon

coupons_api = Blueprint("coupons_api", __name__)

def _sb():
    return current_app.supabase

@coupons_api.post("/api/coupons/validate")
def validate_coupon():
    """
    Body JSON:
      { code, subtotal, msi_selected, email? }
    Respuesta:
      { ok, code, discount_amount, reason?, starts_at_local?, ends_at_local?, cap_mode?, cap_amount?, cap_percent? }
    """
    data = request.get_json(force=True, silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    subtotal = Decimal(str(data.get("subtotal") or "0"))
    msi = bool(data.get("msi_selected"))
    email = (data.get("email") or "").strip() or (getattr(current_user, "email", None) or None)
    user_id = getattr(current_user, "id", None)

    if not code:
        return jsonify(ok=False, reason="missing_code"), 400
    if subtotal <= 0:
        return jsonify(ok=False, reason="subtotal_required"), 400

    sb = _sb()
    row = sb.table("coupons").select("*").eq("code", code).single().execute()
    coupon = row.data
    if not coupon:
        # intento case-insensitive usando índice upper(code)
        row = sb.table("coupons").select("*").eq("upper(code)", code).single().execute()
        coupon = row.data
    if not coupon:
        return jsonify(ok=False, reason="invalid"), 404

    # Vigencia
    if not is_coupon_active(coupon):
        # Fechas bonitas en zona local guardada
        tz = pytz.timezone(coupon.get("timezone") or "America/Monterrey")
        s_local = coupon["starts_at"]; e_local = coupon["ends_at"]
        try:
            s_local = s_local if isinstance(s_local, str) else s_local.isoformat()
            e_local = e_local if isinstance(e_local, str) else e_local.isoformat()
        except Exception:
            pass
        return jsonify(ok=False, reason="inactive",
                       starts_at_local=s_local, ends_at_local=e_local,
                       timezone=coupon.get("timezone")), 400

    # Límites
    ok, why = can_use_coupon(sb, coupon, user_id, email)
    if not ok:
        return jsonify(ok=False, reason=why), 400

    # Mínimo de compra
    min_order = coupon.get("min_order_amount")
    if min_order is not None and Decimal(str(min_order)) > subtotal:
        return jsonify(ok=False, reason="min_order_not_met", min_order_amount=str(min_order)), 400

    # Cálculo
    discount_amount = apply_coupon(subtotal, coupon, msi_selected=msi)
    return jsonify(
        ok=True,
        code=code,
        discount_amount=str(discount_amount),
        cap_mode=coupon.get("cap_mode"),
        cap_amount=str(coupon.get("cap_amount") or "") or None,
        cap_percent=str(coupon.get("cap_percent") or "") or None
    ), 200

@coupons_api.post("/api/coupons/commit")
def commit_coupon():
    """
    Registra el uso de un cupón UNA VEZ que el pedido esté confirmado/pagado.
    Body JSON: { code, order_id, amount, email? }
    """
    data = request.get_json(force=True, silent=True) or {}
    code   = (data.get("code") or "").strip().upper()
    order_id = data.get("order_id")
    amount = Decimal(str(data.get("amount") or "0"))
    email  = (data.get("email") or "").strip() or (getattr(current_user, "email", None) or None)
    user_id = getattr(current_user, "id", None)

    if not code or not order_id or amount <= 0:
        return jsonify(ok=False, reason="missing_fields"), 400

    sb = _sb()
    row = sb.table("coupons").select("id").eq("code", code).single().execute()
    coupon = row.data
    if not coupon:
        return jsonify(ok=False, reason="invalid"), 404

    payload = {
        "coupon_id": coupon["id"],
        "order_id": int(order_id),
        "amount": float(amount),
    }
    if user_id is not None:
        payload["user_id"] = int(user_id)
    if email:
        payload["email"] = email

    ins = sb.table("coupon_redemptions").insert(payload).execute()
    if getattr(ins, "error", None):
        return jsonify(ok=False, reason="insert_failed", detail=str(ins.error)), 400
    return jsonify(ok=True), 200
