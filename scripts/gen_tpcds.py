# scripts/gen_tpcds.py usage: 
# uv run python scripts/gen_tpcds.py 0.1 ~/lab/data/tpcds_sf0_1.duckdb

'''
uv run python scripts/gen_tpcds.py 0.1 ~/lab/data/tpcds_sf0_1.duckdb
uv run python scripts/gen_tpcds.py 10  ~/lab/data/tpcds_sf10.duckdb
'''

import os, sys, duckdb
sf, path = float(sys.argv[1]), os.path.expanduser(sys.argv[2])
con = duckdb.connect(path)
con.execute("SET memory_limit='6GB'")
con.execute(f"SET temp_directory='{os.path.expanduser('~/lab/data/tmp')}'")
con.execute("INSTALL tpcds; LOAD tpcds;")
con.execute(f"CALL dsdgen(sf={sf})")
print(con.execute("SELECT count(*) FROM store_sales").fetchone())
