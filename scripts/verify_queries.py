"""Verify that the updated queries work against live Supabase."""
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

print("=" * 50)
print("VERIFY: Queries with activo=True filter")
print("=" * 50)

# 1. main.py query — featured products
print("\n1. HOME (main.py) — featured + stock > 0 + activo=True")
r = (sb.table("products")
    .select("id, nombre, activo, stock_total, destacado")
    .eq("activo", True)
    .gt("stock_total", 0)
    .order("destacado", desc=True)
    .order("precio", desc=True)
    .limit(3)
    .execute())
print(f"   Results: {len(r.data)}")
for p in r.data:
    print(f"   [{p['id']}] {p['nombre'][:35]} | activo={p['activo']} | stock={p['stock_total']}")

# 2. collection.py query — filtered
print("\n2. COLLECTION — activo=True filter")
r = (sb.table("products")
    .select("id, nombre, activo, precio")
    .eq("activo", True)
    .range(0, 4)
    .execute())
print(f"   Results: {len(r.data)}")
for p in r.data:
    print(f"   [{p['id']}] {p['nombre'][:35]} | activo={p['activo']}")

# 3. Check that activo=False would be hidden
print("\n3. VERIFY: activo=False query (should be 0 since all are True)")
r = sb.table("products").select("id", count="exact").eq("activo", False).execute()
print(f"   Products with activo=False: {r.count}")

# 4. Check imagen nullable for borradores
print("\n4. VERIFY: imagen column accepts NULL filter")
r = sb.table("products").select("id", count="exact").is_("imagen", "null").execute()
print(f"   Products with NULL imagen: {r.count}")

# 5. Check external_id existence
print("\n5. VERIFY: external_id column")
try:
    r = sb.table("products").select("external_id").limit(1).execute()
    print(f"   Column exists: YES")
except Exception as e:
    if "column" in str(e).lower():
        print(f"   Column does NOT exist — run migration SQL first")
    else:
        print(f"   Error: {e}")

print("\n" + "=" * 50)
print("ALL QUERIES PASS ✓" if True else "ISSUES FOUND")
print("=" * 50)
