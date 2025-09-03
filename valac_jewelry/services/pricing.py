from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import List, Dict, Optional
import pytz

def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or "0"))

def _round2(x) -> Decimal:
    return _dec(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def is_coupon_active(coupon: dict, now_utc=None) -> bool:
    """Valida vigencia básica del cupón (active, starts_at, ends_at)."""
    if not coupon or not coupon.get("active"):
        return False
    now_utc = now_utc or datetime.utcnow().replace(tzinfo=pytz.UTC)

    def _to_dt(v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return None
        return v

    starts = _to_dt(coupon.get("starts_at"))
    ends   = _to_dt(coupon.get("ends_at"))

    if starts and starts.tzinfo is None:
        starts = starts.replace(tzinfo=pytz.UTC)
    if ends and ends.tzinfo is None:
        ends = ends.replace(tzinfo=pytz.UTC)

    if starts and now_utc < starts:
        return False
    if ends and now_utc > ends:
        return False
    return True

def apply_coupon(base_amount: Decimal, coupon: dict, msi_selected: bool) -> Decimal:
    """
    Calcula monto de descuento sobre 'base_amount' respetando:
    - type: 'percent' | 'fixed'
    - cap_mode: 'amount' | 'percent' | 'both'
    - cap_amount / cap_percent (+ variantes *_msi)
    """
    base = _dec(base_amount)
    if base <= 0 or not coupon:
        return _dec(0)

    # 1) Descuento bruto
    if (coupon.get("type") or "").lower() == "percent":
        raw = base * (_dec(coupon.get("value", 0)) / _dec(100))
    else:
        raw = _dec(coupon.get("value", 0))

    # 2) Topes
    cap_mode   = coupon.get("cap_mode") or "both"
    cap_amount = coupon.get("cap_amount_msi")  if msi_selected and coupon.get("cap_amount_msi")  is not None else coupon.get("cap_amount")
    cap_pct    = coupon.get("cap_percent_msi") if msi_selected and coupon.get("cap_percent_msi") is not None else coupon.get("cap_percent")

    caps = []
    if cap_mode in ("amount", "both") and cap_amount is not None:
        caps.append(_dec(cap_amount))
    if cap_mode in ("percent", "both") and cap_pct is not None:
        caps.append(base * (_dec(cap_pct) / _dec(100)))

    monto = raw if not caps else min(raw, *caps)
    monto = max(_dec(0), min(monto, base))
    return _round2(monto)

def compute_totals(
    items: List[Dict],
    shipping_base: Decimal,
    free_shipping_threshold: Decimal,
    coupon: Optional[Dict] = None,
    msi_selected: bool = False,
    coupon_percent_base: str = "products",  # 'products' | 'products_plus_shipping'
) -> Dict[str, Decimal]:
    """
    items: [{id, name, unit_price, quantity}]
    Retorna: subtotalProducts, shipping, preCoupon, discount_total, total
    """
    subtotal_products = _round2(sum(_dec(i["unit_price"]) * _dec(i["quantity"]) for i in items))

    # Envío
    if subtotal_products == 0:
        shipping = _dec(0)
    elif subtotal_products >= _dec(free_shipping_threshold):
        shipping = _dec(0)
    else:
        shipping = _round2(shipping_base)

    pre_coupon = _round2(subtotal_products + shipping)

    # Base del % segun config
    base_for_coupon = pre_coupon if coupon_percent_base == "products_plus_shipping" else subtotal_products

    discount_total = _dec(0)
    if coupon and is_coupon_active(coupon):
        discount_total = apply_coupon(base_for_coupon, coupon, msi_selected)

    total = _round2(pre_coupon - discount_total)

    return {
        "subtotalProducts": _round2(subtotal_products),
        "shipping": _round2(shipping),
        "preCoupon": _round2(pre_coupon),
        "discount_total": _round2(discount_total),
        "total": _round2(total),
    }
