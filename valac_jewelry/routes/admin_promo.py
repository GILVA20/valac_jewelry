"""
routes/admin_promo.py
Flask-Admin view for managing promotional banners and hero sections.
"""

import json
import logging
import os
import tempfile
import time
import uuid
from flask import request, redirect, url_for, flash, current_app, jsonify
from flask_admin import BaseView, expose
from flask_login import current_user

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "CatalogoJoyasValacJoyas"
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".webm"}
ALLOWED_EXT = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Keys managed by this view
PROMO_KEYS = [
    "promo_banner_active",
    "promo_banner_messages",
    "promo_banner_bg_color",
    "promo_banner_text_color",
    "promo_section_active",
    "promo_section_title",
    "promo_section_subtitle",
    "promo_section_media_url",
    "promo_section_link",
    "promo_section_link_text",
    "promo_section_bg_color",
]


class PromoAdminView(BaseView):

    def is_accessible(self) -> bool:
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for("auth.login", next=request.url))

    @property
    def app_sb(self):
        return self.admin.app.supabase

    # ── Helpers ──────────────────────────────────────

    def _load_settings(self) -> dict:
        """Load all promo_* keys from site_settings into a dict."""
        try:
            resp = self.app_sb.table("site_settings") \
                .select("key, value") \
                .in_("key", PROMO_KEYS) \
                .execute()
            return {row["key"]: row["value"] for row in (resp.data or [])}
        except Exception as e:
            logger.exception("Error loading promo settings: %s", e)
            return {}

    def _save_setting(self, key: str, value: str) -> None:
        self.app_sb.table("site_settings").upsert({"key": key, "value": value}).execute()

    # ── INDEX ────────────────────────────────────────

    @expose("/")
    def index(self):
        settings = self._load_settings()

        # Parse messages JSON into list for display
        raw_msgs = settings.get("promo_banner_messages", "[]")
        try:
            messages_list = json.loads(raw_msgs)
        except (json.JSONDecodeError, TypeError):
            messages_list = []

        return self.render(
            "admin/promo_settings.html",
            settings=settings,
            messages_list=messages_list,
        )

    # ── SAVE BANNER ──────────────────────────────────

    @expose("/save-banner", methods=["POST"])
    def save_banner(self):
        try:
            # Active toggle
            active = "true" if request.form.get("banner_active") else "false"
            self._save_setting("promo_banner_active", active)

            # Messages: collect non-empty inputs
            messages = []
            for i in range(10):  # support up to 10 messages
                msg = (request.form.get(f"banner_msg_{i}") or "").strip()
                if msg:
                    messages.append(msg)
            self._save_setting("promo_banner_messages", json.dumps(messages, ensure_ascii=False))

            # Colors
            bg = (request.form.get("banner_bg_color") or "#000000").strip()
            text = (request.form.get("banner_text_color") or "#F59E0B").strip()
            self._save_setting("promo_banner_bg_color", bg)
            self._save_setting("promo_banner_text_color", text)

            flash("Banner superior actualizado.", "success")
            logger.info("Promo banner updated by admin: active=%s, %d messages", active, len(messages))
        except Exception as e:
            logger.exception("Error saving banner settings: %s", e)
            flash("Error al guardar configuración del banner.", "error")

        return redirect(url_for(".index"))

    # ── SAVE PROMO SECTION ───────────────────────────

    @expose("/save-section", methods=["POST"])
    def save_section(self):
        try:
            active = "true" if request.form.get("section_active") else "false"
            self._save_setting("promo_section_active", active)

            for field in ["title", "subtitle", "link", "link_text", "bg_color"]:
                key = f"promo_section_{field}"
                val = (request.form.get(f"section_{field}") or "").strip()
                self._save_setting(key, val)

            # media_url: only overwrite if provided in form (upload sets it separately)
            media_url = (request.form.get("section_media_url") or "").strip()
            if media_url:
                self._save_setting("promo_section_media_url", media_url)

            flash("Sección promocional actualizada.", "success")
            logger.info("Promo section updated by admin: active=%s", active)
        except Exception as e:
            logger.exception("Error saving section settings: %s", e)
            flash("Error al guardar sección promocional.", "error")

        return redirect(url_for(".index"))

    # ── UPLOAD MEDIA ─────────────────────────────────

    @expose("/upload-media", methods=["POST"])
    def upload_media(self):
        """Upload image or video to Supabase Storage, return CDN URL."""
        f = request.files.get("media_file")
        if not f or not f.filename:
            return jsonify({"error": "No se seleccionó archivo."}), 400

        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXT:
            return jsonify({"error": f"Formato no soportado: {ext}. Usa: {', '.join(sorted(ALLOWED_EXT))}"}), 400

        # Read file bytes and check size
        file_bytes = f.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            return jsonify({"error": "Archivo demasiado grande. Máximo 50 MB."}), 400

        # Build storage key — flat in products/, same as product images
        filename = f"promo-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}{ext}"
        storage_key = f"products/{filename}"

        # Write to temp file for supabase upload
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        try:
            tmp.write(file_bytes)
            tmp.close()

            mime = f.mimetype or f"{'video' if ext in ALLOWED_VIDEO_EXT else 'image'}/{ext.lstrip('.')}"
            self.app_sb.storage.from_(STORAGE_BUCKET).upload(
                storage_key, tmp.name, {"content-type": mime, "x-upsert": "false"}
            )
        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass

        # CDN only works for images; videos use direct Supabase Storage URL
        is_video = ext in ALLOWED_VIDEO_EXT
        if is_video:
            supabase_url = current_app.config.get("SUPABASE_URL", "")
            public_url = f"{supabase_url}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_key}"
        else:
            cdn = current_app.config.get("CDN_BASE_URL", "").rstrip("/")
            public_url = f"{cdn}/{filename}" if cdn else \
                f"{current_app.config.get('SUPABASE_URL')}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_key}"

        # Save to site_settings
        self._save_setting("promo_section_media_url", public_url)

        logger.info("Promo media uploaded: %s → %s", f.filename, storage_key)
        return jsonify({"url": public_url}), 200
