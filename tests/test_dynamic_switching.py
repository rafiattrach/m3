import m3.config as config_mod
import m3.mcp_server as server
from m3.config import set_active_dataset


def test_dynamic_dataset_switching(tmp_path, monkeypatch):
    # Setup mock data dir
    data_dir = tmp_path / "m3_data"
    data_dir.mkdir()

    # Patch config module to use our temp data dir
    monkeypatch.setattr(config_mod, "_PROJECT_DATA_DIR", data_dir)
    monkeypatch.setattr(config_mod, "_DEFAULT_DATABASES_DIR", data_dir / "databases")
    monkeypatch.setattr(config_mod, "_DEFAULT_PARQUET_DIR", data_dir / "parquet")
    monkeypatch.setattr(config_mod, "_RUNTIME_CONFIG_PATH", data_dir / "config.json")
    monkeypatch.setattr(config_mod, "_CUSTOM_DATASETS_DIR", data_dir / "datasets")

    # Ensure dirs exist
    (data_dir / "databases").mkdir()
    (data_dir / "parquet").mkdir()
    (data_dir / "datasets").mkdir()

    # 1. Start with no active dataset
    # Verify server defaults to mimic-iv-demo (or falls back)
    monkeypatch.setenv("M3_BACKEND", "duckdb")
    monkeypatch.delenv("M3_DB_PATH", raising=False)

    # Ensure config is empty/default
    if (data_dir / "config.json").exists():
        (data_dir / "config.json").unlink()

    # Check default fallback
    ds_def = server._get_active_dataset_def()
    assert ds_def.name == "mimic-iv-demo"

    db_path = server._get_db_path()
    # Should point to demo db in our temp dir
    # Note: get_default_database_path uses the patched _DEFAULT_DATABASES_DIR
    assert "mimic_iv_demo.duckdb" in str(db_path)

    # 2. Set active dataset to something else (simulating 'm3 use')
    # We can use 'mimic-iv-full' as it is registered
    set_active_dataset("mimic-iv-full")

    # Verify config file was written
    assert (data_dir / "config.json").exists()

    # Verify server picks it up
    ds_def = server._get_active_dataset_def()
    assert ds_def.name == "mimic-iv-full"

    db_path = server._get_db_path()
    assert "mimic_iv_full.duckdb" in str(db_path)

    # 3. Simulate environment variable override (static mode)
    monkeypatch.setenv("M3_DB_PATH", "/custom/path/to/db.duckdb")

    db_path = server._get_db_path()
    assert db_path == "/custom/path/to/db.duckdb"

    # Active dataset def should still track the config/env
    ds_def = server._get_active_dataset_def()
    assert ds_def.name == "mimic-iv-full"

    # 4. Unset env var, should go back to dynamic
    monkeypatch.delenv("M3_DB_PATH")
    db_path = server._get_db_path()
    assert "mimic_iv_full.duckdb" in str(db_path)
