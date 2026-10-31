"""One-time setup: wipe existing data and seed the kids table with one row per flat.

- Reads flats from the member-database CSV (duplicates removed, footer row skipped)
- Deletes ALL existing books and kids
- Inserts one kids row per flat with name = NULL (to be filled in later)

Requires kids.name to be nullable — run this once in the Supabase SQL Editor first:
    alter table public.kids alter column name drop not null;

Usage: python setup_kids.py
"""

import csv
import sys
import tomllib
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "Dream Residency Manor, Rajarhat - Member Database.csv"
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def load_flats() -> list[str]:
    """Return sorted unique apartment numbers like '1-Ivory 1B' from the CSV."""
    flats: set[str] = set()
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            block = (row.get("Block") or "").strip()
            unit = (row.get("Unit No") or "").strip()
            if not block or not unit or not block[0].isdigit():
                continue  # skip the "Printed from www.in.adda.io ..." footer row
            flats.add(f"{block} {unit}")
    return sorted(flats)


def main() -> None:
    secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    supabase = create_client(secrets["supabase"]["url"], secrets["supabase"]["key"])

    flats = load_flats()
    print(f"Found {len(flats)} unique flats in {CSV_PATH.name}")

    # books.borrowed_by references kids, so books must be wiped first
    supabase.table("books").delete().neq("id", ZERO_UUID).execute()
    supabase.table("kids").delete().neq("id", ZERO_UUID).execute()
    print("Deleted all existing books and kids.")

    rows = [{"name": None, "apartment_no": apt} for apt in flats]
    try:
        for i in range(0, len(rows), 100):
            supabase.table("kids").insert(rows[i : i + 100]).execute()
    except Exception as e:
        if "null value" in str(e).lower() and "name" in str(e).lower():
            print(
                "\nERROR: kids.name is still NOT NULL. Run this in the Supabase SQL "
                "Editor first:\n"
                "    alter table public.kids alter column name drop not null;"
            )
            sys.exit(1)
        raise

    count = supabase.table("kids").select("id", count="exact").execute().count
    print(f"Done — kids table now has {count} rows, one per flat, name = NULL.")


if __name__ == "__main__":
    main()
