"""Create ~/lab/data/lakehouse.duckdb with one view per Iceberg table, so agents can query
plain table names (store_sales, date_dim, ...) while the data lives in Iceberg.

Usage:
    uv run python scripts/make_views.py            # views over Iceberg (default)
    uv run python scripts/make_views.py --parquet  # fallback: views over the staging Parquet files

Re-run this after every load_iceberg.py run: each load writes a new Iceberg metadata file.
"""
import os
import sys

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

WH = os.path.expanduser("~/lab/data/warehouse")
VIEWS_DB = os.path.expanduser("~/lab/data/lakehouse.duckdb")
NAMESPACE = "tpcds"
USE_PARQUET = "--parquet" in sys.argv

catalog = SqlCatalog("lab", uri=f"sqlite:///{WH}/catalog.db", warehouse=f"file://{WH}")

con = duckdb.connect(VIEWS_DB)
if not USE_PARQUET:
    con.execute("INSTALL iceberg; LOAD iceberg;")

for identifier in catalog.list_tables(NAMESPACE):
    name = identifier[-1]
    if USE_PARQUET:
        source = f"read_parquet('{WH}/staging/{name}.parquet')"
    else:
        table = catalog.load_table(f"{NAMESPACE}.{name}")
        metadata = table.metadata_location.removeprefix("file://")
        source = f"iceberg_scan('{metadata}')"
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {source}")
    print(f"view {name:<28} -> {'parquet' if USE_PARQUET else 'iceberg'}")

con.close()
print(f"\nDone. Views written to {VIEWS_DB}. Next: uv run python scripts/check_views.py")