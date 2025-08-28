from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import pytz

def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or "0"))

def _round2(x) -> Decimal:
    return _dec(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def is_coupon_active(coupon: dict, now_utc=None) -> bool:
    """
    coupon: dict de la tabla coupons
    """
    if not coupon or not coupon.get("active"):
        return False
    now_utc = now_utc or datetime.utcnow().replace(tzinfo=pytz.UTC)
    return (coupon["starts_at"] <= now_utc.isoformat() if isinstance(coupon["starts_at"], str) else coupon["starts_at"] <= now_utc) and \
           (coupon["ends_at"]   >= now_utc.isoformat() if isinstance(coupon["ends_at"],   str) else coupon["ends_at"]   >= now_utc)

def apply_coupon(subtotal_after_product_discounts, coupon: dict, msi_selected: bool) -> Decimal:
    """
    Calcula monto de descuento respetando cap_mode + caps de MSI.
    """
    base = _dec(subtotal_after_product_discounts)
    if base <= 0:
        return _dec(0)

    # 1) descuento bruto por tipo
    if coupon["type"] == "percent":
        raw = base * (_dec(coupon["value"]) / _dec(100))
    else:  # fixed
        raw = _dec(coupon["value"])

    # 2) topes según modo y MSI
    cap_mode = coupon.get("cap_mode") or "both"
    cap_amount     = coupon.get("cap_amount_msi")  if msi_selected and coupon.get("cap_amount_msi")  is not None else coupon.get("cap_amount")
    cap_percent    = coupon.get("cap_percent_msi") if msi_selected and coupon.get("cap_percent_msi") is not None else coupon.get("cap_percent")

    caps = []
    if cap_mode in ("amount", "both") and cap_amount is not None:
        caps.append(_dec(cap_amount))
    if cap_mode in ("percent", "both") and cap_percent is not None:
        caps.append(base * (_dec(cap_percent) / _dec(100)))

    monto = raw if not caps else min(raw, *caps)
    monto = max(_dec(0), min(monto, base))
    return _round2(monto)
