from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_NAME = "federated-tabPFN"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def configs(self) -> Path:
        return self.root / "configs"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def cache(self) -> Path:
        return self.root / ".cache"

    @property
    def huggingface_cache(self) -> Path:
        return self.cache / "huggingface"

    @property
    def openml_cache(self) -> Path:
        return self.cache / "openml"

    @property
    def matplotlib_cache(self) -> Path:
        return self.cache / "matplotlib"

    @property
    def tabpfn_cache(self) -> Path:
        return self.cache / "tabpfn"


def default_paths() -> ProjectPaths:
    return ProjectPaths(root=Path(__file__).resolve().parents[2])
