"""
routes/admin_reviews.py
Flask-Admin view para moderación de reseñas de clientes.
"""

import logging
from flask import request, redirect, url_for, flash, current_app
from flask_admin import BaseView, expose
from flask_login import current_user

logger = logging.getLogger(__name__)


class ReviewsAdminView(BaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_accessible(self) -> bool:
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for("auth.login", next=request.url))

    @property
    def app_sb(self):
        return self.admin.app.supabase

    # ── INDEX: listar reseñas ────────────────────────

    @expose("/")
    def index(self):
        sb = self.app_sb
        status_filter = request.args.get("status", "all")
        stars_filter = request.args.get("estrellas", type=int)

        try:
            q = sb.table("reviews").select("*")
            if status_filter == "pending":
                q = q.eq("verificado", "false")
            elif status_filter == "approved":
                q = q.eq("verificado", "true")

            if stars_filter and 1 <= stars_filter <= 5:
                q = q.eq("estrellas", stars_filter)

            resp = q.order("created_at", desc=True).execute()
            reviews = resp.data or []
        except Exception as e:
            logger.exception("Error al listar reseñas admin: %s", e)
            reviews = []
            flash("Error al cargar reseñas.", "error")

        cdn = current_app.config.get("CDN_BASE_URL", "")

        # Conteos rápidos
        try:
            total_resp = sb.table("reviews").select("id", count="exact").execute()
            pending_resp = sb.table("reviews").select("id", count="exact").eq("verificado", "false").execute()
            approved_resp = sb.table("reviews").select("id", count="exact").eq("verificado", "true").execute()
            stats = {
                "total": total_resp.count or 0,
                "pending": pending_resp.count or 0,
                "approved": approved_resp.count or 0,
            }
        except Exception:
            stats = {"total": 0, "pending": 0, "approved": 0}

        return self.render(
            "admin/reviews_admin.html",
            reviews=reviews,
            stats=stats,
            cdn=cdn,
            status_filter=status_filter,
            stars_filter=stars_filter,
            auto_approve=self._get_auto_approve(),
        )

    # ── HELPERS ───────────────────────────────────────

    def _get_auto_approve(self) -> bool:
        """Lee el setting reviews_auto_approve de site_settings."""
        try:
            resp = self.app_sb.table("site_settings").select("value").eq("key", "reviews_auto_approve").single().execute()
            return (resp.data or {}).get("value", "false") == "true"
        except Exception:
            return False

    # ── TOGGLE AUTO-APPROVE ──────────────────────────

    @expose("/toggle-auto-approve", methods=["POST"])
    def toggle_auto_approve(self):
        sb = self.app_sb
        current = self._get_auto_approve()
        new_value = "false" if current else "true"
        try:
            sb.table("site_settings").upsert({"key": "reviews_auto_approve", "value": new_value}).execute()
            estado = "activada" if new_value == "true" else "desactivada"
            flash(f"Aprobación automática {estado}.", "success")
            logger.info("Auto-approve reseñas cambiado a %s por admin", new_value)
        except Exception as e:
            logger.exception("Error al cambiar auto-approve: %s", e)
            flash("Error al cambiar configuración.", "error")
        return redirect(url_for(".index"))

    # ── APROBAR ──────────────────────────────────────

    @expose("/approve/<int:review_id>", methods=["POST"])
    def approve(self, review_id: int):
        sb = self.app_sb
        try:
            sb.table("reviews").update({"verificado": True, "admin_notes": None}).eq("id", review_id).execute()
            flash("Reseña aprobada exitosamente.", "success")
            logger.info("Reseña %s aprobada por admin", review_id)
        except Exception as e:
            logger.exception("Error al aprobar reseña %s: %s", review_id, e)
            flash("Error al aprobar la reseña.", "error")
        return redirect(url_for(".index"))

    # ── RECHAZAR ─────────────────────────────────────

    @expose("/reject/<int:review_id>", methods=["POST"])
    def reject(self, review_id: int):
        sb = self.app_sb
        notes = (request.form.get("admin_notes") or "").strip()
        try:
            sb.table("reviews").update({
                "verificado": False,
                "admin_notes": notes or "Rechazada por admin",
            }).eq("id", review_id).execute()
            flash("Reseña rechazada.", "warning")
            logger.info("Reseña %s rechazada por admin", review_id)
        except Exception as e:
            logger.exception("Error al rechazar reseña %s: %s", review_id, e)
            flash("Error al rechazar la reseña.", "error")
        return redirect(url_for(".index"))

    # ── ELIMINAR ─────────────────────────────────────

    @expose("/delete/<int:review_id>", methods=["POST"])
    def delete(self, review_id: int):
        sb = self.app_sb
        try:
            # Obtener media_urls antes de borrar
            resp = sb.table("reviews").select("media_urls").eq("id", review_id).execute()
            if resp.data:
                media_urls = resp.data[0].get("media_urls") or []
                # Eliminar archivos del Storage
                for path in media_urls:
                    try:
                        # media_urls guarda cdn-relative paths; Storage necesita path completo
                        storage_path = f"products/{path}" if not path.startswith("products/") else path
                        sb.storage.from_("CatalogoJoyasValacJoyas").remove([storage_path])
                    except Exception as storage_err:
                        logger.warning("No se pudo eliminar archivo %s: %s", path, storage_err)

            sb.table("reviews").delete().eq("id", review_id).execute()
            flash("Reseña y archivos eliminados.", "success")
            logger.info("Reseña %s eliminada por admin", review_id)
        except Exception as e:
            logger.exception("Error al eliminar reseña %s: %s", review_id, e)
            flash("Error al eliminar la reseña.", "error")
        return redirect(url_for(".index"))
