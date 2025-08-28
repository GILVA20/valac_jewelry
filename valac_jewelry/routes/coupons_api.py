# valac_jewelry/routes/coupons_api.py
from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app, session
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from ..services.limits_service import can_use_coupon

coupons_api = Blueprint("coupons_api", __name__, url_prefix="/api/coupons")

def _round2(x) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def _parse_utc(ts: str) -> datetime:
    # Maneja '2025-08-01T00:00:00Z' y variantes
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

def _compute_discount(coupon: dict, subtotal: float, msi_selected: bool) -> float:
    """
    Calcula el descuento y aplica cap según modo y si es MSI.
    Campos esperados en coupon:
      - type: 'percent' | 'fixed'
      - value
      - cap_mode: 'amount' | 'percent' | 'both' | None
      - cap_amount, cap_percent
      - cap_amount_msi, cap_percent_msi
    """
    if subtotal <= 0:
        return 0.0

    ctype = (coupon.get("type") or "").lower()
    value = float(coupon.get("value") or 0)

    if ctype == "percent":
        raw = subtotal * (value / 100.0)
    else:  # fixed
        raw = value

    # Caps
    cmode = (coupon.get("cap_mode") or "").lower() or "both"
    cap_amt = float(coupon.get("cap_amount") or 0)
    cap_pct = float(coupon.get("cap_percent") or 0)

    # Caps MSI
    if msi_selected:
        cap_amt = float(coupon.get("cap_amount_msi") or cap_amt)
        cap_pct = float(coupon.get("cap_percent_msi") or cap_pct)

    # Aplica caps
    capped = raw
    if cmode in ("amount", "both") and cap_amt > 0:
        capped = min(capped, cap_amt)
    if cmode in ("percent", "both") and cap_pct > 0:
        capped = min(capped, subtotal * (cap_pct / 100.0))

    return _round2(max(0.0, min(capped, subtotal)))

@coupons_api.route("/validate", methods=["POST"])
def validate_coupon():
    try:
        data = request.get_json(silent=True) or {}
        code = (data.get("code") or "").strip().upper()
        subtotal = float(data.get("subtotal") or 0)
        msi_selected = bool(data.get("msi_selected", False))

        if not code or subtotal <= 0:
            return jsonify({"ok": False, "reason": "invalid"}), 400

        sb = current_app.supabase

        # Busca cupón por código
        r = sb.table("coupons").select("*").eq("code", code).single().execute()
        coupon = r.data or None
        if not coupon:
            return jsonify({"ok": False, "reason": "invalid"}), 200

        # Activo + vigencia
        if not bool(coupon.get("active", True)):
            return jsonify({"ok": False, "reason": "inactive"}), 200

        now = datetime.now(timezone.utc)
        try:
            starts = _parse_utc(coupon["starts_at"])
            ends = _parse_utc(coupon["ends_at"])
        except Exception:
            return jsonify({"ok": False, "reason": "inactive"}), 200

        if not (starts <= now <= ends):
            return jsonify({"ok": False, "reason": "inactive"}), 200

        # Mínimo de compra
        min_order = float(coupon.get("min_order_amount") or 0)
        if subtotal < min_order:
            return jsonify({"ok": False, "reason": "min_order_not_met"}), 200

        # Límites global/usuario
        # Obtén user_id/email de tu sesión (ajusta a tu app)
        user_id = session.get("user_id")
        email = (session.get("user_email") or session.get("checkout_email") or "").strip().lower()

        ok, why = can_use_coupon(sb, coupon, user_id, email)
        if not ok:
            return jsonify({"ok": False, "reason": why}), 200

        # Cálculo de descuento con caps
        discount = _compute_discount(coupon, subtotal, msi_selected)
        return jsonify({
            "ok": True,
            "discount_amount": discount,
            "coupon_id": coupon["id"],
            "code": coupon["code"]
        }), 200

    except Exception as e:
        current_app.logger.exception("[/api/coupons/validate] error: %s", e)
        return jsonify({"ok": False, "reason": "server_error"}), 500
