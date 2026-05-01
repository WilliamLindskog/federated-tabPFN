from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .results_summary import recent_result_rows

SUPPORTED_PHASES = ("engineering", "iid-core", "overall")


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


def phase_specs(config: dict[str, Any], phase: str) -> list[RunSpec]:
    if phase == "engineering":
        dataset = "adult_engineering_slice"
        baselines = [str(b) for b in config.get("baselines", [])]
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
        study_plan = dict(config.get("study_plan", {}))
        dataset = "tabpfn_paper_cc18_numerical_18"
        baselines = [str(b) for b in study_plan.get("primary_core_baselines", [])]
        return [
            RunSpec(
                dataset=dataset,
                baseline=baseline,
                split_regime="iid",
                run_name=f"paper-{baseline_run_slug(baseline)}-iid",
            )
            for baseline in baselines
        ]

    if phase == "overall":
        return phase_specs(config, "engineering") + phase_specs(config, "iid-core")

    raise ValueError(f"Unsupported phase '{phase}'. Expected one of: {', '.join(SUPPORTED_PHASES)}.")


def _blocked_reason(spec: RunSpec, supported_baselines: set[str]) -> str | None:
    if spec.dataset != "adult_engineering_slice":
        return "dataset execution path not implemented yet"
    if spec.baseline not in supported_baselines:
        return "unsupported baseline"
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
