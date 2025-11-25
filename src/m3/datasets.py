from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class DatasetDefinition:
    name: str
    description: str = ""
    version: str = "1.0"
    file_listing_url: str | None = None
    subdirectories_to_scan: list[str] = field(default_factory=list)
    default_duckdb_filename: str | None = None
    primary_verification_table: str | None = None
    tags: list[str] = field(default_factory=list)

    # For backward compatibility or ease of use, we might add a way to access as dict if needed,
    # but we'll try to use object access.

    # BigQuery Configuration
    bigquery_project_id: str | None = "physionet-data"
    bigquery_dataset_ids: list[str] = field(default_factory=list)

    # Authentication & Download Helpers
    requires_authentication: bool = False

    def __post_init__(self):
        if not self.default_duckdb_filename:
            self.default_duckdb_filename = f"{self.name.replace('-', '_')}.duckdb"


class DatasetRegistry:
    _registry: ClassVar[dict[str, DatasetDefinition]] = {}

    @classmethod
    def register(cls, dataset: DatasetDefinition):
        cls._registry[dataset.name.lower()] = dataset

    @classmethod
    def get(cls, name: str) -> DatasetDefinition | None:
        return cls._registry.get(name.lower())

    @classmethod
    def list_all(cls) -> list[DatasetDefinition]:
        return list(cls._registry.values())

    @classmethod
    def reset(cls):
        cls._registry.clear()
        cls._register_builtins()

    @classmethod
    def _register_builtins(cls):
        # Built-in datasets
        mimic_iv_demo = DatasetDefinition(
            name="mimic-iv-demo",
            description="MIMIC-IV Clinical Database Demo",
            file_listing_url="https://physionet.org/files/mimic-iv-demo/2.2/",
            subdirectories_to_scan=["hosp", "icu"],
            primary_verification_table="hosp_admissions",
            tags=["mimic", "clinical", "demo"],
            bigquery_project_id=None,
            bigquery_dataset_ids=None,
        )

        mimic_iv_full = DatasetDefinition(
            name="mimic-iv-full",
            description="MIMIC-IV Clinical Database (Full)",
            file_listing_url="https://physionet.org/files/mimiciv/3.1/",
            subdirectories_to_scan=["hosp", "icu"],
            primary_verification_table="hosp_admissions",
            tags=["mimic", "clinical", "full"],
            bigquery_project_id="physionet-data",
            bigquery_dataset_ids=["mimiciv_3_1_hosp", "mimiciv_3_1_icu"],
            requires_authentication=True,
        )

        cls.register(mimic_iv_demo)
        cls.register(mimic_iv_full)


# Initialize registry
DatasetRegistry._register_builtins()
