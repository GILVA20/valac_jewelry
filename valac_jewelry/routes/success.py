# routes/success.py
from flask import Blueprint, render_template, session, flash, redirect, url_for, current_app
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

success_bp = Blueprint('success', __name__)

# =========================
# Utilidades
# =========================
_MONEY_RX = re.compile(r"[^\d\.\-]")  # quita todo menos dígitos, punto y signo -

def _to_float(v, default=0.0):
    if v is None:
        return float(default)
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).strip()
        s = _MONEY_RX.sub("", s.replace(",", "."))
        return float(s) if s not in ("", ".", "-", "-.") else float(default)
    except Exception:
        return float(default)

def _get_shipping(cart_snapshot, order):
    cs = cart_snapshot or {}
    candidates = [
        cs.get("shipping"), cs.get("envio"), cs.get("shipping_cost"),
        cs.get("costo_envio"), cs.get("costo_envío"),
        (order or {}).get("shipping"), (order or {}).get("costo_envio"), (order or {}).get("costo_envío"),
    ]
    for c in candidates:
        val = _to_float(c, None)
        if val is not None:
            return val
    return 0.0

# =========================
# Normalización de items
# =========================
def _normalize_items(order_items):
    """
    Devuelve items con:
      id, nombre, descripcion, imagen, cantidad, precio, descuento, unit_price, final_price, line_total
    Sin repartir aún el descuento a nivel snapshot.
    """
    norm = []
    for it in (order_items or []):
        precio     = _to_float(it.get("precio") or it.get("unit_price"))
        descuento  = _to_float(it.get("descuento", it.get("discount", 0.0)))
        cantidad   = int(_to_float(it.get("cantidad") or it.get("quantity") or 1, 1))
        final_raw  = it.get("final_price")
        final_unit = _to_float(final_raw, precio - descuento)

        norm.append({
            "id": it.get("id"),
            "nombre": it.get("nombre") or it.get("title"),
            "descripcion": it.get("descripcion") or it.get("description"),
            "imagen": it.get("imagen") or it.get("image"),
            "cantidad": cantidad,
            "precio": round(precio, 2),
            "descuento": round(descuento, 2),
            "unit_price": round(precio, 2),
            "final_price": round(final_unit, 2),
            "line_total": round(final_unit * cantidad, 2),
        })
    return norm

def _apply_snapshot_discount_fallback(items, cart_snapshot):
    """
    Si TODOS los items no tienen descuento (final == unit y descuento == 0) pero
    cart_snapshot sí trae discount_total > 0, repartir proporcionalmente y
    AJUSTAR centavos en el último ítem para cuadrar EXACTO con el snapshot.
    """
    if not items:
        return items

    discount_total = _to_float(cart_snapshot.get("discount_total"))
    if discount_total <= 0:
        return items

    all_without_discount = all(
        abs(it["final_price"] - it["unit_price"]) < 1e-9 and abs(it["descuento"]) < 1e-9
        for it in items
    )
    if not all_without_discount:
        return items  # ya traen descuentos por ítem; respetar

    # Subtotal previo al descuento
    pre_subtotals = [round(it["unit_price"] * it["cantidad"], 2) for it in items]
    pre_sum = round(sum(pre_subtotals), 2)
    if pre_sum <= 0:
        return items

    # Reparto proporcional por línea (en valor de línea)
    line_discounts = []
    running = 0.0
    for i, pre in enumerate(pre_subtotals):
        if i < len(items) - 1:
            portion = round((pre / pre_sum) * discount_total, 2)
            line_discounts.append(portion)
            running += portion
        else:
            # Ajuste final para cuadrar exactamente con discount_total
            portion = round(discount_total - running, 2)
            line_discounts.append(portion)

    # Convertir a unitario y recalcular finales
    new_items = []
    for it, line_disc in zip(items, line_discounts):
        qty = max(1, int(it["cantidad"]))
        unit_disc = round(line_disc / qty, 2)
        final_unit = round(it["unit_price"] - unit_disc, 2)
        new_items.append({
            **it,
            "descuento": unit_disc,
            "final_price": final_unit,
            "line_total": round(final_unit * qty, 2),
        })

    # Ajuste de redondeo: asegurar que suma líneas = pre_sum - discount_total
    expected_after = round(pre_sum - discount_total, 2)
    computed_after = round(sum(x["line_total"] for x in new_items), 2)
    delta = round(expected_after - computed_after, 2)

    if abs(delta) >= 0.01:
        # Ajustamos el último ítem a nivel unitario (recalcular line_total)
        last = new_items[-1]
        qty = max(1, int(last["cantidad"]))
        # mover delta a precio final unitario
        last["final_price"] = round(last["final_price"] + (delta / qty), 2)
        last["line_total"]  = round(last["final_price"] * qty, 2)
        new_items[-1] = last

        # Revalidar
        computed_after = round(sum(x["line_total"] for x in new_items), 2)
        if abs(expected_after - computed_after) >= 0.01:
            current_app.logger.warning(
                "Ajuste de centavos no cuadró exacto: esperado=%.2f calculado=%.2f",
                expected_after, computed_after
            )

    return new_items

# =========================
# Correo
# =========================
def send_order_confirmation_email(order, order_items, cart_snapshot):
    try:
        smtp_server = current_app.config.get("MAIL_SERVER")
        smtp_port = current_app.config.get("MAIL_PORT")
        sender_email = current_app.config.get("MAIL_SENDER")
        sender_password = current_app.config.get("MAIL_PASSWORD")
        recipient_email = order.get("email")

        html_content = render_template(
            "email/order_success_email.html",
            order=order,
            order_items=order_items,
            cart_snapshot=cart_snapshot
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Gracias por tu compra #{order['id']} en VALAC Joyas"
        msg["From"] = sender_email
        msg["To"] = recipient_email
        recipients = [recipient_email]
        if sender_email and sender_email != recipient_email:
            msg["Bcc"] = sender_email
            recipients.append(sender_email)

        msg.attach(MIMEText(html_content, "html"))
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            if sender_password:
                server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())

        current_app.logger.info("Correo de confirmación enviado a %s", recipient_email)
    except Exception as e:
        current_app.logger.error("Error al enviar el correo de confirmación: %s", e)

# =========================
# Handler SUCCESS
# =========================
@success_bp.route('/success', methods=['GET'])
def success():
    order = session.get("order_data")
    order_items = session.get("order_items", [])
    cart_snapshot = session.get("cart_snapshot")

    if not order or not cart_snapshot:
        flash("No se encontró información de la orden.", "error")
        current_app.logger.error("SUCCESS: order_data o cart_snapshot es None.")
        return redirect(url_for("main.home"))

    # Totales desde snapshot (fuente de verdad)
    order["subtotal"] = _to_float(cart_snapshot.get("subtotalProducts"))
    order["discount"] = _to_float(cart_snapshot.get("discount_total"))
    order["total"]    = _to_float(cart_snapshot.get("total"))
    order["shipping"] = _get_shipping(cart_snapshot, order)
    order["estado_pago"] = order.get("estado_pago", "Completado")

    # 1) Normalizar ítems
    items = _normalize_items(order_items)

    # 2) Reparto proporcional si hace falta + ajuste de centavos
    items = _apply_snapshot_discount_fallback(items, cart_snapshot)

    # 3) Verificaciones (y números que puedes mostrar para depurar si quieres)
    items_sum = round(sum(i["line_total"] for i in items), 2)
    expected_items_sum = round(order["subtotal"] - order["discount"], 2)
    if abs(items_sum - expected_items_sum) >= 0.01:
        current_app.logger.warning(
            "Items != snapshot: sum(items)=%.2f vs esperado=%.2f",
            items_sum, expected_items_sum
        )

    grand_sum = round(items_sum + order["shipping"], 2)
    if abs(grand_sum - order["total"]) >= 0.01:
        current_app.logger.warning(
            "Items+shipping != total: calc=%.2f vs total=%.2f",
            grand_sum, order["total"]
        )

    # 4) Enviar correo (mismos datos)
    send_order_confirmation_email(order, items, cart_snapshot)

    current_app.logger.debug(
        "SUCCESS Render: id=%s subtotal=%.2f discount=%.2f shipping=%.2f total=%.2f items_sum=%.2f",
        order.get("id"), order["subtotal"], order["discount"], order["shipping"], order["total"], items_sum
    )

    current_app.logger.debug(
        "SUCCESS VIEW CHECK -> items_sum=%.2f, shipping=%.2f, grand_sum=%.2f, total=%.2f",
        items_sum, order["shipping"], grand_sum, order["total"]
    )

    return render_template(
        'success.html',
        order=order,
        order_items=items,
        cart_snapshot=cart_snapshot,
        items_sum=items_sum,   # subtotal de artículos (suma de line_total)
        grand_sum=grand_sum    # artículos + envío
)