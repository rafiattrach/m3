from pathlib import Path

from m3.config import (
    get_dataset_config,
    get_dataset_raw_files_path,
    get_default_database_path,
)


def test_get_dataset_config_known():
    cfg = get_dataset_config("mimic-iv-demo")
    assert isinstance(cfg, dict)
    assert cfg.get("default_db_filename") == "mimic_iv_demo.db"


def test_get_dataset_config_unknown():
    assert get_dataset_config("not-a-dataset") is None


def test_default_paths(tmp_path, monkeypatch):
    # Redirect default dirs to a temp location
    import m3.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "DEFAULT_DATABASES_DIR", tmp_path / "dbs")
    monkeypatch.setattr(cfg_mod, "DEFAULT_RAW_FILES_DIR", tmp_path / "raw")
    db_path = get_default_database_path("mimic-iv-demo")
    raw_path = get_dataset_raw_files_path("mimic-iv-demo")
    # They should be Path objects and exist
    assert isinstance(db_path, Path)
    assert db_path.parent.exists()
    assert isinstance(raw_path, Path)
    assert raw_path.exists()


def test_raw_path_includes_dataset_name(tmp_path, monkeypatch):
    import m3.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "DEFAULT_RAW_FILES_DIR", tmp_path / "raw")
    raw_path = get_dataset_raw_files_path("mimic-iv-demo")
    assert "mimic-iv-demo" in str(raw_path)
