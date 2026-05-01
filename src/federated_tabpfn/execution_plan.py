from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .results_summary import recent_result_rows
from .study_registry import dataset_key, dataset_slug, paper_cc18_datasets

SUPPORTED_PHASES = (
    "engineering",
    "iid-core",
    "noniid-label-core",
    "noniid-quantity-core",
    "noniid-feature-core",
    "noniid-core",
    "overall",
)


@dataclass(frozen=True)
class RunSpec:
    dataset: str
    baseline: str
    split_regime: str
    run_name: str


@dataclass(frozen=True)
class BlockedSpec:
    spec: RunSpec
    reason: str


@dataclass(frozen=True)
class PhasePlan:
    phase: str
    runnable: list[RunSpec]
    skipped: list[RunSpec]
    blocked: list[BlockedSpec]


def baseline_run_slug(baseline: str) -> str:
    if baseline == "logistic_regression":
        return "logreg"
    return baseline.replace("_", "-")


def completed_run_keys() -> set[tuple[str, str, str]]:
    return {
        (str(row.get("dataset")), str(row.get("baseline")), str(row.get("split_regime")))
        for row in recent_result_rows(limit=None)
    }


def _paper_core_baselines(config: dict[str, Any]) -> list[str]:
    study_plan = dict(config.get("study_plan", {}))
    return [str(b) for b in study_plan.get("primary_core_baselines", [])]


def _paper_track_specs(config: dict[str, Any], split_regime: str) -> list[RunSpec]:
    baselines = _paper_core_baselines(config)
    return [
        RunSpec(
            dataset=dataset_key(dataset),
            baseline=baseline,
            split_regime=split_regime,
            run_name=f"paper-{dataset.data_id}-{dataset_slug(dataset)}-{baseline_run_slug(baseline)}-{split_regime.replace('_', '-')}",
        )
        for dataset in paper_cc18_datasets()
        for baseline in baselines
    ]


def phase_specs(config: dict[str, Any], phase: str) -> list[RunSpec]:
    if phase == "engineering":
        dataset = "adult_engineering_slice"
        study_plan = dict(config.get("study_plan", {}))
        engineering_baselines = ["logistic_regression", *[str(b) for b in study_plan.get("primary_core_baselines", [])]]
        baselines = list(dict.fromkeys(engineering_baselines))
        split_regimes = [str(s) for s in config.get("split_regimes", [])]
        return [
            RunSpec(
                dataset=dataset,
                baseline=baseline,
                split_regime=split_regime,
                run_name=f"adult-{baseline_run_slug(baseline)}-{split_regime.replace('_', '-')}",
            )
            for baseline in baselines
            for split_regime in split_regimes
        ]

    if phase == "iid-core":
        return _paper_track_specs(config, "iid")

    if phase == "noniid-label-core":
        return _paper_track_specs(config, "label_skew")

    if phase == "noniid-quantity-core":
        return _paper_track_specs(config, "quantity_skew")

    if phase == "noniid-feature-core":
        return _paper_track_specs(config, "feature_skew")

    if phase == "noniid-core":
        study_plan = dict(config.get("study_plan", {}))
        order = [
            str(item)
            for item in study_plan.get(
                "preferred_non_iid_order",
                ["label_skew", "quantity_skew", "feature_skew"],
            )
        ]
        specs: list[RunSpec] = []
        for split_regime in order:
            if split_regime not in {"label_skew", "quantity_skew", "feature_skew"}:
                raise ValueError(
                    f"Unsupported non-IID split '{split_regime}' in preferred_non_iid_order. "
                    "Expected only 'label_skew', 'quantity_skew', and/or 'feature_skew'."
                )
            specs.extend(_paper_track_specs(config, split_regime))
        return specs

    if phase == "overall":
        return phase_specs(config, "engineering") + phase_specs(config, "iid-core")

    raise ValueError(f"Unsupported phase '{phase}'. Expected one of: {', '.join(SUPPORTED_PHASES)}.")


def _blocked_reason(spec: RunSpec, supported_baselines: set[str]) -> str | None:
    if spec.baseline not in supported_baselines:
        return "unsupported baseline"
    if spec.dataset != "adult_engineering_slice" and not spec.dataset.startswith("openml:"):
        return "dataset execution path not implemented yet"
    return None


def build_phase_plan(
    config: dict[str, Any],
    phase: str,
    *,
    supported_baselines: set[str],
) -> PhasePlan:
    completed = completed_run_keys()
    runnable: list[RunSpec] = []
    skipped: list[RunSpec] = []
    blocked: list[BlockedSpec] = []

    for spec in phase_specs(config, phase):
        run_key = (spec.dataset, spec.baseline, spec.split_regime)
        if run_key in completed:
            skipped.append(spec)
            continue
        reason = _blocked_reason(spec, supported_baselines)
        if reason:
            blocked.append(BlockedSpec(spec=spec, reason=reason))
            continue
        runnable.append(spec)

    return PhasePlan(phase=phase, runnable=runnable, skipped=skipped, blocked=blocked)


def format_phase_plan(plan: PhasePlan) -> str:
    lines = [
        f"Phase: {plan.phase}",
        f"Runnable runs: {len(plan.runnable)}",
        f"Skipped completed: {len(plan.skipped)}",
        f"Blocked unsupported: {len(plan.blocked)}",
    ]
    if plan.runnable:
        lines.extend(["", "Runnable:"])
        for spec in plan.runnable:
            lines.append(f"- {spec.dataset} | {spec.baseline} | {spec.split_regime} | {spec.run_name}")
    if plan.blocked:
        lines.extend(["", "Blocked:"])
        for item in plan.blocked:
            spec = item.spec
            lines.append(f"- {spec.dataset} | {spec.baseline} | {spec.split_regime} | {item.reason}")
    if plan.skipped:
        lines.extend(["", "Skipped:"])
        for spec in plan.skipped:
            lines.append(f"- {spec.dataset} | {spec.baseline} | {spec.split_regime}")
    return "\n".join(lines)
