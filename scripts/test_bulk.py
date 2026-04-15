"""Test rápido del bulk upload con el CSV de prueba."""
import sys, io
sys.path.insert(0, ".")

with open("ProductosPrueba_Bulk.csv", "rb") as f:
    raw = f.read()

from valac_jewelry.routes.admin_bulk_upload import process_csv

result = process_csv(io.BytesIO(raw))
valid  = result["valid_rows"]
errors = result["errors"]

print(f"✅ Productos válidos : {len(valid)}")
print(f"⚠️  Warnings         : {len(errors)}")
print()

for p in valid:
    costo    = p.get("precio_costo")
    precio   = p.get("precio")
    costo_s  = f"${costo:.2f}" if costo else "?"
    precio_s = f"${precio:.2f}" if precio else "?"
    dev      = p.get("devolucion_a") or "-"
    print(
        f"  [{p['tipo_oro']:10s}] {p['nombre']:35s} | {p['tipo_producto']:10s} "
        f"| costo={costo_s:>10s}  pf={precio_s:>10s} "
        f"| inv={p['estado_inventario']:12s}  dev={dev}"
    )

if errors:
    print("\nWarnings:")
    for e in errors:
        print(f"  {e}")
