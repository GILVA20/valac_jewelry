"""Quick schema check against live Supabase."""
import os, sys
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    print("ERROR: SUPABASE_URL or SUPABASE_KEY not set"); sys.exit(1)

sb = create_client(url, key)

# 1. Check products columns
print("=" * 50)
print("1. PRODUCTS TABLE — column check")
print("=" * 50)
try:
    r = sb.table("products").select("*").limit(1).execute()
    if r.data:
        cols = sorted(r.data[0].keys())
        print(f"   Columns ({len(cols)}): {', '.join(cols)}")
        has_estado = "estado" in cols
        has_extid = "external_id" in cols
        print(f"   estado column: {'YES' if has_estado else 'NO — MIGRATION NEEDED'}")
        print(f"   external_id column: {'YES' if has_extid else 'NO — MIGRATION NEEDED'}")
    else:
        print("   Table exists but is empty")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Check if imagen is nullable (try insert with NULL)
print()
print("=" * 50)
print("2. PRODUCTS.imagen nullable check")
print("=" * 50)
try:
    r = sb.table("products").select("imagen").is_("imagen", "null").limit(1).execute()
    print(f"   Products with NULL imagen: {len(r.data)}")
    print("   (If query succeeds, column accepts NULL filter)")
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Sample products
print()
print("=" * 50)
print("3. SAMPLE PRODUCTS (first 3)")
print("=" * 50)
try:
    r = sb.table("products").select("id, nombre, precio, tipo_oro, imagen, stock_total").limit(3).execute()
    for p in r.data or []:
        img = "HAS_IMG" if p.get("imagen") else "NO_IMG"
        print(f"   [{p['id']}] {p.get('nombre','?')} | ${p.get('precio',0)} | {p.get('tipo_oro','?')} | {img} | stock={p.get('stock_total',0)}")
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Check all tables
print()
print("=" * 50)
print("4. OTHER TABLES — existence check")
print("=" * 50)
tables = ["product_images", "orders", "coupons", "coupon_redemptions", "product_views", "user_navigation"]
for t in tables:
    try:
        r = sb.table(t).select("*", count="exact").limit(0).execute()
        count = r.count if hasattr(r, 'count') and r.count is not None else "?"
        print(f"   {t}: EXISTS (rows: {count})")
    except Exception as e:
        print(f"   {t}: NOT FOUND or ERROR — {e}")

# 5. Check RLS impact on estado filter
print()
print("=" * 50)
print("5. RLS CHECK — can anon key filter by estado?")
print("=" * 50)
try:
    r = sb.table("products").select("id").eq("estado", "activo").limit(1).execute()
    print(f"   Filter by estado='activo': OK ({len(r.data)} results)")
except Exception as e:
    err_str = str(e)
    if "column" in err_str.lower() and "does not exist" in err_str.lower():
        print(f"   COLUMN 'estado' DOES NOT EXIST — run migration first!")
    else:
        print(f"   ERROR (possibly RLS): {e}")

print()
print("=" * 50)
print("DONE")
print("=" * 50)
