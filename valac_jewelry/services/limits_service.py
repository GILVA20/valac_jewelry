from __future__ import annotations
from typing import Optional, Tuple

def _count(sb, table: str, **eq):
    q = sb.table(table).select("id", count="exact")
    for k, v in eq.items():
        q = q.eq(k, v)
    r = q.execute()
    return r.count or 0

def can_use_coupon(sb, coupon: dict, user_id: Optional[int], email: Optional[str]) -> Tuple[bool, str]:
    """
    Verifica limites: max_uses (global) y max_uses_per_user (por usuario/email).
    """
    cid = coupon["id"]
    # Global
    if coupon.get("max_uses") is not None:
        used = _count(sb, "coupon_redemptions", coupon_id=cid)
        if used >= int(coupon["max_uses"]):
            return False, "limit_reached_global"

    # Por usuario (prefiere user_id; si no, email)
    per_user = coupon.get("max_uses_per_user")
    if per_user is not None and int(per_user) > 0:
        if user_id is not None:
            used_u = _count(sb, "coupon_redemptions", coupon_id=cid, user_id=user_id)
            if used_u >= int(per_user):
                return False, "limit_reached_user"
        elif email:
            used_e = _count(sb, "coupon_redemptions", coupon_id=cid, email=email)
            if used_e >= int(per_user):
                return False, "limit_reached_user"

    return True, "ok"
