"""
Deduplicate products by nombre.
Keeps the row with the most data (imagen not null, highest id).
Run with --dry-run first to preview, then without to delete.

Usage:
    python scripts/deduplicate_products.py --dry-run
    python scripts/deduplicate_products.py --delete
"""

import os, sys, argparse
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]


def get_all_products(sb):
    """Fetch all products ordered by nombre, id."""
    rows = []
    offset = 0
    batch = 1000
    while True:
        resp = sb.table("products").select("id, nombre, imagen, activo, created_at").order("nombre").order("id").range(offset, offset + batch - 1).execute()
        if not resp.data:
            break
        rows.extend(resp.data)
        if len(resp.data) < batch:
            break
        offset += batch
    return rows


def find_duplicates(products):
    """Group by nombre and pick which to keep vs delete."""
    from collections import defaultdict
    groups = defaultdict(list)
    for p in products:
        groups[p["nombre"]].append(p)

    to_delete = []
    for nombre, dupes in groups.items():
        if len(dupes) < 2:
            continue
        # Sort: prefer activo=True, then has imagen, then highest id
        dupes.sort(key=lambda p: (
            p.get("activo") is True,
            bool(p.get("imagen")),
            p["id"],
        ), reverse=True)
        keep = dupes[0]
        remove = dupes[1:]
        to_delete.append({"nombre": nombre, "keep": keep, "remove": remove})
    return to_delete


def main():
    parser = argparse.ArgumentParser(description="Deduplicate products by nombre")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview duplicates without deleting")
    group.add_argument("--delete", action="store_true", help="Actually delete duplicate rows")
    args = parser.parse_args()

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    products = get_all_products(sb)
    print(f"Total products: {len(products)}")

    duplicates = find_duplicates(products)
    if not duplicates:
        print("No duplicates found.")
        return

    total_remove = sum(len(d["remove"]) for d in duplicates)
    print(f"\nFound {len(duplicates)} duplicated names ({total_remove} rows to remove):\n")

    for d in duplicates:
        keep = d["keep"]
        print(f'  "{d["nombre"]}"')
        print(f'    KEEP   id={keep["id"]}  activo={keep.get("activo")}  imagen={"yes" if keep.get("imagen") else "no"}')
        for r in d["remove"]:
            print(f'    DELETE id={r["id"]}  activo={r.get("activo")}  imagen={"yes" if r.get("imagen") else "no"}')

    if args.dry_run:
        print(f"\n[DRY RUN] Would delete {total_remove} duplicate rows. Re-run with --delete to execute.")
        return

    # Actually delete
    ids_to_delete = []
    for d in duplicates:
        for r in d["remove"]:
            ids_to_delete.append(r["id"])

    print(f"\nDeleting {len(ids_to_delete)} rows...")
    # Delete in batches of 50
    for i in range(0, len(ids_to_delete), 50):
        batch = ids_to_delete[i:i+50]
        sb.table("product_images").delete().in_("product_id", batch).execute()
        sb.table("products").delete().in_("id", batch).execute()
        print(f"  Deleted batch {i//50 + 1} ({len(batch)} rows)")

    print("Done. Duplicates removed.")


if __name__ == "__main__":
    main()
