# valac_jewelry/services/limits_service.py
from __future__ import annotations
from typing import Optional, Tuple
from flask import current_app

def _count(sb, table: str, **eq) -> int:
    """
    Cuenta filas de forma robusta. Si el gateway no envía el header de conteo,
    cae al tamaño de data. Si la tabla no existe o hay error, regresa 0
    (y loguea warning).
    """
    q = sb.table(table).select("id", count="exact")
    for k, v in eq.items():
        q = q.eq(k, v)
    try:
        r = q.execute()
        return r.count if getattr(r, "count", None) is not None else len(r.data or [])
    except Exception as e:
        current_app.logger.warning(f"[_count] fallo en {table} filtros={eq}: {e}")
        return 0

def can_use_coupon(sb, coupon: dict, user_id: Optional[int], email: Optional[str]) -> Tuple[bool, str]:
    """
    Verifica límites: max_uses (global) y max_uses_per_user (por usuario/email).
    - Por email se normaliza a lower() para evitar duplicados por capitalización.
    """
    cid = coupon["id"]

    # Límite global
    if coupon.get("max_uses") is not None:
        used = _count(sb, "coupon_redemptions", coupon_id=cid)
        if used >= int(coupon["max_uses"]):
            return False, "limit_reached_global"

    # Límite por usuario (prefiere user_id; si no, email normalizado)
    per_user = coupon.get("max_uses_per_user")
    if per_user is not None and int(per_user) > 0:
        if user_id is not None:
            used_u = _count(sb, "coupon_redemptions", coupon_id=cid, user_id=user_id)
            if used_u >= int(per_user):
                return False, "limit_reached_user"
        else:
            email_norm = (email or "").strip().lower()
            if email_norm:
                used_e = _count(sb, "coupon_redemptions", coupon_id=cid, email=email_norm)
                if used_e >= int(per_user):
                    return False, "limit_reached_user"

    return True, "ok"
