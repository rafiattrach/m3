from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class DatasetDefinition:
    name: str
    description: str = ""
    version: str = "1.0"
    file_listing_url: Optional[str] = None
    subdirectories_to_scan: List[str] = field(default_factory=list)
    default_duckdb_filename: Optional[str] = None
    primary_verification_table: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # For backward compatibility or ease of use, we might add a way to access as dict if needed, 
    # but we'll try to use object access.

    def __post_init__(self):
        if not self.default_duckdb_filename:
            self.default_duckdb_filename = f"{self.name.replace('-', '_')}.duckdb"

class DatasetRegistry:
    _registry: Dict[str, DatasetDefinition] = {}

    @classmethod
    def register(cls, dataset: DatasetDefinition):
        cls._registry[dataset.name.lower()] = dataset

    @classmethod
    def get(cls, name: str) -> Optional[DatasetDefinition]:
        return cls._registry.get(name.lower())

    @classmethod
    def list_all(cls) -> List[DatasetDefinition]:
        return list(cls._registry.values())

    @classmethod
    def reset(cls):
        cls._registry.clear()
        cls._register_builtins()

    @classmethod
    def _register_builtins(cls):
        # Built-in datasets
        demo = DatasetDefinition(
            name="mimic-iv-demo",
            description="MIMIC-IV Clinical Database Demo",
            file_listing_url="https://physionet.org/files/mimic-iv-demo/2.2/",
            subdirectories_to_scan=["hosp", "icu"],
            primary_verification_table="hosp_admissions",
            tags=["mimic", "clinical", "demo"]
        )

        full = DatasetDefinition(
            name="mimic-iv-full",
            description="MIMIC-IV Clinical Database (Full)",
            file_listing_url=None, # Requires auth, manual download instructions
            subdirectories_to_scan=["hosp", "icu"],
            primary_verification_table="hosp_admissions",
            tags=["mimic", "clinical", "full"]
        )

        cls.register(demo)
        cls.register(full)

# Initialize registry
DatasetRegistry._register_builtins()

