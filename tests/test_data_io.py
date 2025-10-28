import duckdb

from m3.data_io import compute_parquet_dir_size, verify_table_rowcount


def test_compute_parquet_dir_size_empty(tmp_path):
    size = compute_parquet_dir_size(tmp_path)
    assert size == 0


def test_verify_table_rowcount_with_temp_duckdb(tmp_path):
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE VIEW temp_numbers AS SELECT 1 AS x UNION ALL SELECT 2 AS x")
        con.commit()
    finally:
        con.close()

    count = verify_table_rowcount(db_path, "temp_numbers")
    assert count == 2
