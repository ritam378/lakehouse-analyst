"""Check that every view in lakehouse.duckdb returns the same row count as the source DuckDB file,
then run one real TPC-DS-style query through the views.

Usage:
    uv run python scripts/check_views.py ~/lab/data/tpcds_sf7.duckdb

Full sequence (test on the tiny copy first, then the real data):
    uv run python scripts/load_iceberg.py ~/lab/data/tpcds_sf0_1.duckdb
    uv run python scripts/make_views.py
    uv run python scripts/check_views.py ~/lab/data/tpcds_sf0_1.duckdb

    uv run python scripts/load_iceberg.py ~/lab/data/tpcds_sf7.duckdb
    uv run python scripts/make_views.py
    uv run python scripts/check_views.py ~/lab/data/tpcds_sf7.duckdb
"""
import os
import sys

import duckdb

SRC_DB = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/lab/data/tpcds_sf7.duckdb")
VIEWS_DB = os.path.expanduser("~/lab/data/lakehouse.duckdb")

src = duckdb.connect(SRC_DB, read_only=True)
lake = duckdb.connect(VIEWS_DB, read_only=True)
lake.execute("SET memory_limit='6GB'")
try:
    lake.execute("INSTALL iceberg; LOAD iceberg")
except duckdb.Error:
    print("Note: iceberg extension unavailable; fine if you built Parquet views with --parquet")

ok = True
for (t,) in src.execute("SHOW TABLES").fetchall():
    expected = src.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    got = lake.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    status = "OK " if expected == got else "MISMATCH"
    ok &= expected == got
    print(f"{status} {t:<28} source {expected:>12,}  lakehouse {got:>12,}")

print("\nSample query: top 5 item categories by store revenue in 2001")
print(lake.execute("""
    SELECT i_category, round(sum(ss_net_paid), 2) AS revenue
    FROM store_sales
    JOIN date_dim ON ss_sold_date_sk = d_date_sk
    JOIN item     ON ss_item_sk = i_item_sk
    WHERE d_year = 2001
    GROUP BY i_category
    ORDER BY revenue DESC
    LIMIT 5
""").df().to_string(index=False))

print("\nALL GOOD" if ok else "\nSome tables don't match; re-run load_iceberg.py, then make_views.py")