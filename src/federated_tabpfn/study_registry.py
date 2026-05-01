from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StudyDataset:
    data_id: int
    name: str
    n_instances: int
    n_features: int
    n_classes: int


# This is the exact 18-dataset numerical/no-missing OpenML-CC18 subset described
# in the original TabPFN paper, derived from the authors' own reduced CC18 list.
TABPFN_PAPER_CC18_NUMERICAL_18: tuple[StudyDataset, ...] = (
    StudyDataset(11, "balance-scale", 625, 4, 3),
    StudyDataset(14, "mfeat-fourier", 2000, 76, 10),
    StudyDataset(16, "mfeat-karhunen", 2000, 64, 10),
    StudyDataset(18, "mfeat-morphological", 2000, 6, 10),
    StudyDataset(22, "mfeat-zernike", 2000, 47, 10),
    StudyDataset(37, "diabetes", 768, 8, 2),
    StudyDataset(54, "vehicle", 846, 18, 4),
    StudyDataset(458, "analcatdata_authorship", 841, 70, 4),
    StudyDataset(1049, "pc4", 1458, 37, 2),
    StudyDataset(1050, "pc3", 1563, 37, 2),
    StudyDataset(1063, "kc2", 522, 21, 2),
    StudyDataset(1068, "pc1", 1109, 21, 2),
    StudyDataset(1462, "banknote-authentication", 1372, 4, 2),
    StudyDataset(1464, "blood-transfusion-service-center", 748, 4, 2),
    StudyDataset(1494, "qsar-biodeg", 1055, 41, 2),
    StudyDataset(1510, "wdbc", 569, 30, 2),
    StudyDataset(40982, "steel-plates-fault", 1941, 27, 7),
    StudyDataset(40994, "climate-model-simulation-crashes", 540, 18, 2),
)


def paper_cc18_dataset_ids() -> list[int]:
    return [dataset.data_id for dataset in TABPFN_PAPER_CC18_NUMERICAL_18]


def paper_cc18_datasets() -> tuple[StudyDataset, ...]:
    return TABPFN_PAPER_CC18_NUMERICAL_18


def dataset_slug(dataset: StudyDataset) -> str:
    return dataset.name.replace("_", "-")


def dataset_key(dataset: StudyDataset) -> str:
    return f"openml:{dataset.data_id}:{dataset_slug(dataset)}"


def parse_dataset_key(selected_dataset: str) -> StudyDataset | None:
    if not selected_dataset.startswith("openml:"):
        return None
    parts = selected_dataset.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"Malformed OpenML dataset key '{selected_dataset}'.")
    data_id = int(parts[1])
    for dataset in TABPFN_PAPER_CC18_NUMERICAL_18:
        if dataset.data_id == data_id:
            return dataset
    raise ValueError(f"OpenML dataset id {data_id} is not in the locked paper-track registry.")


def study_registry_payload() -> dict[str, Any]:
    return {
        "paper_track": {
            "name": "tabpfn_paper_cc18_numerical_18",
            "source": "OpenML-CC18",
            "description": (
                "Exact small numerical, no-missing OpenML-CC18 subset used for the original "
                "TabPFN paper's headline numerical benchmark."
            ),
            "dataset_count": len(TABPFN_PAPER_CC18_NUMERICAL_18),
            "dataset_ids": paper_cc18_dataset_ids(),
            "datasets": [asdict(dataset) for dataset in TABPFN_PAPER_CC18_NUMERICAL_18],
        },
        "execution_tracks": {
            "engineering": "adult_engineering_slice",
            "paper": "tabpfn_paper_cc18_numerical_18",
            "holdout": "tabpfn_paper_openml_numerical_holdout",
        },
    }


def format_study_registry() -> str:
    lines = [
        "TabPFN Paper Dataset Track",
        "",
        "Track: tabpfn_paper_cc18_numerical_18",
        f"Dataset count: {len(TABPFN_PAPER_CC18_NUMERICAL_18)}",
        "",
        "Datasets:",
    ]
    for dataset in TABPFN_PAPER_CC18_NUMERICAL_18:
        lines.append(
            f"- {dataset.data_id} | {dataset.name} | n={dataset.n_instances} | p={dataset.n_features} | classes={dataset.n_classes}"
        )
    return "\n".join(lines)
