import gzip
from unittest import mock

import duckdb
import requests

from m3.data_io import (
    COMMON_USER_AGENT,
    _scrape_urls_from_html_page,
    compute_parquet_dir_size,
    convert_csv_to_parquet,
    init_duckdb_from_parquet,
    verify_table_rowcount,
)


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


# ------------------------------------------------------------
# Scraping tests
# ------------------------------------------------------------


class DummyResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content.encode()
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(response=self)

    @property
    def reason(self):
        return "Error"

    def iter_content(self, chunk_size=1):
        yield from self.content


def test_scrape_urls(monkeypatch):
    html = (
        "<html><body>"
        '<a href="file1.csv.gz">ok</a>'
        '<a href="skip.txt">no</a>'
        "</body></html>"
    )
    dummy = DummyResponse(html)
    session = requests.Session()
    monkeypatch.setattr(session, "get", lambda url, timeout=None: dummy)
    urls = _scrape_urls_from_html_page("http://example.com/", session)
    assert urls == ["http://example.com/file1.csv.gz"]


def test_scrape_no_matching_suffix(monkeypatch):
    html = '<html><body><a href="file1.txt">ok</a></body></html>'
    dummy = DummyResponse(html)
    session = requests.Session()
    monkeypatch.setattr(session, "get", lambda url, timeout=None: dummy)
    urls = _scrape_urls_from_html_page("http://example.com/", session)
    assert urls == []


def test_common_user_agent_header():
    # Ensure the constant is set and looks like a UA string
    assert isinstance(COMMON_USER_AGENT, str)
    assert "Mozilla/" in COMMON_USER_AGENT


# ------------------------------------------------------------
# CSV -> Parquet conversion and DuckDB init tests
# ------------------------------------------------------------


def _write_gz_csv(path, text):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def test_convert_csv_to_parquet_and_init_duckdb(tmp_path, monkeypatch):
    # Prepare a minimal CSV.gz under hosp/
    src_root = tmp_path / "src"
    hosp_dir = src_root / "hosp"
    hosp_dir.mkdir(parents=True, exist_ok=True)
    csv_gz = hosp_dir / "sample.csv.gz"

    _write_gz_csv(
        csv_gz,
        "col1,col2\n"  # header
        "1,foo\n"
        "2,bar\n",
    )

    # Convert to Parquet under dst root
    dst_root = tmp_path / "parquet"
    ok = convert_csv_to_parquet("mimic-iv-demo", src_root, dst_root)
    assert ok  # conversion succeeded

    out_parquet = dst_root / "hosp" / "sample.parquet"
    assert out_parquet.exists()  # parquet file created

    # Quick verify via DuckDB
    con = duckdb.connect()
    try:
        cnt = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{out_parquet.as_posix()}')"
        ).fetchone()[0]
    finally:
        con.close()
    assert cnt == 2  # two data rows

    # Initialize DuckDB views, patching the parquet root resolver
    db_path = tmp_path / "test.duckdb"
    with mock.patch("m3.data_io.get_dataset_parquet_root", return_value=dst_root):
        init_ok = init_duckdb_from_parquet("mimic-iv-demo", db_path)
    assert init_ok  # views created

    # Query the created view name hosp_sample
    con = duckdb.connect(str(db_path))
    try:
        cnt = con.execute("SELECT COUNT(*) FROM hosp_sample").fetchone()[0]
    finally:
        con.close()
    assert cnt == 2
