"""Load every TPC-DS table from a DuckDB file into Iceberg tables (local SQLite catalog).

Usage (from ~/lab/lakehouse-analyst):
    uv run python scripts/load_iceberg.py ~/lab/data/tpcds_sf0_1.duckdb   # quick test, ~1 minute
    uv run python scripts/load_iceberg.py ~/lab/data/tpcds_sf7.duckdb    # real run, ~10-30 minutes

Re-running replaces the tables, so it is safe to run the small one first and the big one after.
"""
import os
import sys
import time

import duckdb
import pyarrow as pa
import pyarrow.dataset as ds
from pyiceberg.catalog.sql import SqlCatalog

SRC_DB = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/lab/data/tpcds_sf7.duckdb")
WH = os.path.expanduser("~/lab/data/warehouse")
STAGING = f"{WH}/staging"
NAMESPACE = "tpcds"
BATCH_ROWS = 2_000_000  # rows appended per Iceberg write; lower this if you run short of RAM

os.makedirs(STAGING, exist_ok=True)

catalog = SqlCatalog(
    "lab",
    uri=f"sqlite:///{WH}/catalog.db",
    warehouse=f"file://{WH}",
)
catalog.create_namespace_if_not_exists(NAMESPACE)

con = duckdb.connect(SRC_DB, read_only=True)
con.execute("SET memory_limit='6GB'")

tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
print(f"Found {len(tables)} tables in {SRC_DB}")

for t in tables:
    start = time.time()
    identifier = f"{NAMESPACE}.{t}"

    # 1. Export to a Parquet staging file (DuckDB streams this, so memory stays low).
    pq = f"{STAGING}/{t}.parquet"
    con.execute(f"COPY {t} TO '{pq}' (FORMAT parquet)")

    # 2. Replace the Iceberg table if it already exists, so re-runs don't duplicate data.
    if catalog.table_exists(identifier):
        catalog.drop_table(identifier)

    data = ds.dataset(pq, format="parquet")
    table = catalog.create_table(identifier, schema=data.schema)

    # 3. Append in batches to stay within 16 GB of RAM.
    #    Parquet yields small chunks, so group them into ~BATCH_ROWS before each commit.
    rows, pending, pending_rows = 0, [], 0
    for batch in data.to_batches():
        if batch.num_rows == 0:
            continue
        pending.append(batch)
        pending_rows += batch.num_rows
        if pending_rows >= BATCH_ROWS:
            table.append(pa.Table.from_batches(pending))
            rows += pending_rows
            pending, pending_rows = [], 0
    if pending:
        table.append(pa.Table.from_batches(pending))
        rows += pending_rows

    print(f"{t:<28} {rows:>12,} rows  {time.time() - start:6.1f}s")

con.close()
print("\nDone. Next: uv run python scripts/make_views.py")