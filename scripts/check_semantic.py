"""Check semantic/tpcds.yaml against a real database: every table, column and join must exist.

Usage:
    uv run python scripts/check_semantic.py ~/lab/data/tpcds_sf0_1.duckdb
"""
import os
import sys

import duckdb
import yaml

DB = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/lab/data/tpcds_sf0_1.duckdb")
sem = yaml.safe_load(open("semantic/tpcds.yaml"))
con = duckdb.connect(DB, read_only=True)

errors = 0
print(f"{len(sem['tables'])} tables in semantic layer")

for table, spec in sem["tables"].items():
    for key in ("description", "grain", "columns"):
        if key not in spec:
            print(f"MISSING {table}.{key}")
            errors += 1

    # 1. Every documented column must exist.
    for col in spec.get("columns", {}):
        try:
            con.execute(f"SELECT {col} FROM {table} LIMIT 1")
        except duckdb.Error as e:
            print(f"BAD COLUMN {table}.{col}: {e}")
            errors += 1

    # 2. Every documented join must run and match at least one row.
    for other, cond in spec.get("joins", {}).items():
        try:
            n = con.execute(f"SELECT count(*) FROM (SELECT 1 FROM {table} JOIN {other} ON {cond} LIMIT 1)").fetchone()[0]
            if n == 0:
                print(f"EMPTY JOIN {table} -> {other}: {cond}")
                errors += 1
        except duckdb.Error as e:
            print(f"BAD JOIN {table} -> {other}: {e}")
            errors += 1

    print(f"checked {table:<18} {len(spec.get('columns', {})):>3} columns  {len(spec.get('joins', {})):>2} joins")

print("\nALL GOOD" if errors == 0 else f"\n{errors} problem(s)")
sys.exit(1 if errors else 0)
