#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_images_webp.py
======================
Migra TODAS las imágenes existentes en Supabase Storage a WebP optimizado (≤1200px, q80).

Flujo por imagen:
  1. Descarga la imagen original del bucket.
  2. Convierte a WebP con Pillow (1200px max, calidad 80).
  3. Sube la versión optimizada con clave nueva (.webp).
  4. Actualiza la URL en la(s) tabla(s) de Supabase (products.imagen, product_images.imagen).
  5. Elimina el archivo original del bucket.

Uso:
  python scripts/migrate_images_webp.py          # Dry-run (solo muestra qué haría)
  python scripts/migrate_images_webp.py --apply  # Ejecuta la migración real

Variables de entorno requeridas:
  SUPABASE_URL          – URL del proyecto Supabase
  SUPABASE_SERVICE_KEY  – Service-role key (con permisos de Storage admin)
                          Si no existe, intenta con SUPABASE_KEY (anon).

Requisitos:
  pip install supabase pillow requests
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

# Cargar .env automáticamente (busca en la raíz del proyecto)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # sin python-dotenv, usa variables de entorno del sistema

import requests
from PIL import Image

# ── Config ──────────────────────────────────────────────────────────────────
BUCKET = "CatalogoJoyasValacJoyas"
MAX_DIMENSION = 1200
WEBP_QUALITY = 80
SKIP_EXTENSIONS = {".webp"}  # No re-procesar imágenes que ya son .webp
# ────────────────────────────────────────────────────────────────────────────


def get_supabase_client():
    """Crea y devuelve un cliente Supabase (service key preferred)."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("ERROR: Configura SUPABASE_URL y SUPABASE_SERVICE_KEY (o SUPABASE_KEY).")
        sys.exit(1)
    if not os.environ.get("SUPABASE_SERVICE_KEY"):
        print("⚠  SUPABASE_SERVICE_KEY no encontrado; usando SUPABASE_KEY (anon). "
              "Puede fallar por permisos de Storage.")
    return create_client(url, key)


def extract_storage_path(public_url: str) -> str | None:
    """
    Dado una URL pública de Supabase Storage, extrae el path relativo al bucket.
    Ejemplo:
      https://xxx.supabase.co/storage/v1/object/public/Bucket/products/abc.jpg
      → products/abc.jpg
    """
    parsed = urlparse(public_url.split("?")[0])  # quitar query params (?t=...)
    path = parsed.path
    # El path suele ser /storage/v1/object/public/<bucket>/<key>
    marker = f"/object/public/{BUCKET}/"
    idx = path.find(marker)
    if idx >= 0:
        return path[idx + len(marker):]
    # Fallback: intentar con /object/sign/
    marker2 = f"/object/sign/{BUCKET}/"
    idx2 = path.find(marker2)
    if idx2 >= 0:
        return path[idx2 + len(marker2):]
    return None


def download_image(url: str) -> bytes | None:
    """Descarga una imagen desde su URL pública."""
    try:
        resp = requests.get(url.split("?")[0], timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"  ✗ Error descargando {url}: {e}")
        return None


def optimize_image(raw_bytes: bytes) -> tuple[bytes, int, int] | None:
    """Convierte bytes de imagen a WebP optimizado. Retorna (bytes, w, h) o None."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        if max(img.size) > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=WEBP_QUALITY, optimize=True)
        return buf.getvalue(), img.size[0], img.size[1]
    except Exception as e:
        print(f"  ✗ Error Pillow: {e}")
        return None


def already_webp(url: str) -> bool:
    """Comprueba si la URL ya apunta a un .webp."""
    clean = url.split("?")[0].lower()
    return any(clean.endswith(ext) for ext in SKIP_EXTENSIONS)


def get_public_url(sb, storage_key: str) -> str:
    """Obtiene la URL pública de un archivo en el bucket."""
    result = sb.storage.from_(BUCKET).get_public_url(storage_key)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return (result.get("publicUrl") or result.get("publicURL") or
                (result.get("data") or {}).get("publicUrl") or
                (result.get("data") or {}).get("publicURL") or "")
    return str(result) if result else ""


def migrate_image(sb, table: str, row_id: str, current_url: str, *, dry_run: bool) -> bool:
    """Migra una imagen individual. Retorna True si se procesó."""
    if already_webp(current_url):
        print(f"  ⏭  Ya es .webp — {current_url[:80]}")
        return False

    old_key = extract_storage_path(current_url)
    if not old_key:
        print(f"  ✗ No pude extraer storage path de: {current_url[:100]}")
        return False

    # Generar nueva clave
    new_key = f"products/{int(time.time() * 1000)}-{uuid.uuid4().hex}.webp"

    if dry_run:
        original_ext = os.path.splitext(old_key)[1]
        print(f"  [DRY-RUN] {table}.{row_id}: {old_key} ({original_ext}) → {new_key}")
        return True

    # 1. Descargar
    raw = download_image(current_url)
    if not raw:
        return False
    original_size = len(raw)

    # 2. Optimizar
    result = optimize_image(raw)
    if not result:
        return False
    webp_bytes, w, h = result
    new_size = len(webp_bytes)

    # 3. Subir la nueva versión
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webp")
    try:
        tmp.write(webp_bytes)
        tmp_path = tmp.name
        tmp.close()
        sb.storage.from_(BUCKET).upload(
            new_key, tmp_path,
            {"content-type": "image/webp", "x-upsert": "false"}
        )
    except Exception as e:
        print(f"  ✗ Error subiendo {new_key}: {e}")
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return False
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    # 4. Obtener URL pública nueva
    new_url = get_public_url(sb, new_key)
    if not new_url:
        print(f"  ✗ No se pudo obtener URL pública para {new_key}")
        return False

    # 5. Actualizar DB
    try:
        sb.table(table).update({"imagen": new_url}).eq("id", row_id).execute()
    except Exception as e:
        print(f"  ✗ Error actualizando {table}.{row_id}: {e}")
        return False

    # 6. Borrar archivo original
    try:
        sb.storage.from_(BUCKET).remove([old_key])
    except Exception as e:
        print(f"  ⚠  No se pudo borrar original {old_key}: {e}")

    savings_pct = (1 - new_size / original_size) * 100 if original_size > 0 else 0
    print(f"  ✓ {table}.{row_id}: {original_size // 1024}KB → {new_size // 1024}KB "
          f"({savings_pct:.0f}% ahorro) [{w}x{h}]")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrar imágenes existentes a WebP optimizado.")
    parser.add_argument("--apply", action="store_true",
                        help="Ejecutar la migración real (sin esto, solo dry-run)")
    args = parser.parse_args()
    dry_run = not args.apply

    if dry_run:
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  MODO DRY-RUN – No se modificará nada. Usa --apply para    ║")
        print("║  ejecutar la migración real.                                ║")
        print("╚══════════════════════════════════════════════════════════════╝")
    else:
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  MODO APPLY – Migrando imágenes a WebP…                    ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    sb = get_supabase_client()

    # ── 1. Tabla products ───────────────────────────────────────────────────
    print("\n━━━ Tabla: products (campo imagen) ━━━")
    products_resp = sb.table("products").select("id, imagen").not_.is_("imagen", "null").execute()
    products = products_resp.data or []
    print(f"  Encontrados: {len(products)} productos con imagen")

    migrated = 0
    skipped = 0
    errors = 0
    for p in products:
        if not p.get("imagen"):
            continue
        ok = migrate_image(sb, "products", p["id"], p["imagen"], dry_run=dry_run)
        if ok:
            migrated += 1
        elif already_webp(p["imagen"]):
            skipped += 1
        else:
            errors += 1

    # ── 2. Tabla product_images ─────────────────────────────────────────────
    print("\n━━━ Tabla: product_images (campo imagen) ━━━")
    gallery_resp = sb.table("product_images").select("id, imagen").not_.is_("imagen", "null").execute()
    gallery = gallery_resp.data or []
    print(f"  Encontrados: {len(gallery)} imágenes de galería")

    for g in gallery:
        if not g.get("imagen"):
            continue
        ok = migrate_image(sb, "product_images", g["id"], g["imagen"], dry_run=dry_run)
        if ok:
            migrated += 1
        elif already_webp(g["imagen"]):
            skipped += 1
        else:
            errors += 1

    # ── Resumen ─────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    action = "migradas" if not dry_run else "por migrar"
    print(f"  Imágenes {action}: {migrated}")
    print(f"  Ya eran .webp (omitidas): {skipped}")
    print(f"  Errores: {errors}")
    print("═" * 60)


if __name__ == "__main__":
    main()
