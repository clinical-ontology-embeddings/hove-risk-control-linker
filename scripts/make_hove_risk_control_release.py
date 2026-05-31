#!/usr/bin/env python3
"""Generate public-release artifacts for the HOVE Risk-Control Linker.

The generator intentionally emits only public-safe artifacts:

- A public-facing model card.
- A machine-readable performance table JSON and Markdown.
- A release manifest with sanitized filenames and no row-level predictions.
- Optional figure copies if source figures are available.

Internal version strings, absolute paths, and raw row-level predictions are not
included in the generated public outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_NAME = "HOVE Risk-Control Linker"
RELEASE_ID = "hove-risk-control-linker"
CHECKPOINT_SANITIZED_NAME = "risk_control_linker.pt"
CHECKPOINT_CONFIG_NAME = "risk_control_linker_config.json"
DECISION_THRESHOLD = 0.45
OVERVIEW_FIGURE_PNG = "hove_risk_control_linker_overview.png"
OVERVIEW_FIGURE_PDF = "hove_risk_control_linker_overview.pdf"
ACKNOWLEDGEMENT_TEXT = (
    "This research was supported by the AI Computing Infrastructure Enhancement "
    "(GPU Rental Support) User Support Program funded by the Ministry of Science "
    "and ICT (MSIT), Republic of Korea (No. RQT-25-120164)."
)


@dataclass(frozen=True)
class MainRow:
    name: str
    f1: float
    exact: float
    link_acc: float
    severity_per_gold: float
    hdfp_per_row: float


@dataclass(frozen=True)
class AblationRow(MainRow):
    threshold: float | None = None
    positive_rate: float | None = None


@dataclass(frozen=True)
class BootstrapDelta:
    variant: str
    f1: float
    exact: float
    link_acc: float
    severity: float
    hdfp: float
    f1_ci: tuple[float, float]
    exact_ci: tuple[float, float]
    link_acc_ci: tuple[float, float]
    severity_ci: tuple[float, float]
    hdfp_ci: tuple[float, float]


DEFAULT_MAIN_ROWS: tuple[MainRow, ...] = (
    MainRow(
        name="unfiltered top3",
        f1=0.4310,
        exact=0.4840,
        link_acc=0.9007,
        severity_per_gold=7.3207,
        hdfp_per_row=1.9527,
    ),
    MainRow(
        name="similarity >=0.85",
        f1=0.5572,
        exact=0.4721,
        link_acc=0.9123,
        severity_per_gold=4.3149,
        hdfp_per_row=0.7326,
    ),
    MainRow(
        name="base scalar reference",
        f1=0.5719734921498721,
        exact=0.4651370740397764,
        link_acc=0.9088892248048229,
        severity_per_gold=4.036752543190438,
        hdfp_per_row=0.6117217430267727,
    ),
    MainRow(
        name="risk-aware scalar reference",
        f1=0.5760327307356187,
        exact=0.45714402728511716,
        link_acc=0.9112671329178799,
        severity_per_gold=3.89478665868803,
        hdfp_per_row=0.5375378066539711,
    ),
    MainRow(
        name="HOVE Risk-Control Linker",
        f1=0.6659730198280197,
        exact=0.47941671008652875,
        link_acc=0.9118949213424794,
        severity_per_gold=2.8357500563130964,
        hdfp_per_row=0.16103954295956088,
    ),
)

DEFAULT_ABLATION_ROWS: tuple[AblationRow, ...] = (
    AblationRow(
        name="final true risk-aware near123",
        threshold=0.45,
        positive_rate=0.3487,
        f1=0.6660,
        exact=0.4794,
        link_acc=0.9119,
        severity_per_gold=2.8358,
        hdfp_per_row=0.1610,
    ),
    AblationRow(
        name="matched true risk-aware near123",
        threshold=0.10,
        positive_rate=0.3493,
        f1=0.6449,
        exact=0.4691,
        link_acc=0.9137,
        severity_per_gold=3.0236,
        hdfp_per_row=0.2121,
    ),
    AblationRow(
        name="exact-only",
        threshold=0.05,
        positive_rate=0.3184,
        f1=0.6091,
        exact=0.4706,
        link_acc=0.9944,
        severity_per_gold=3.1339,
        hdfp_per_row=0.2155,
    ),
    AblationRow(
        name="randomized risk-aware near123",
        threshold=0.05,
        positive_rate=0.3521,
        f1=0.6458,
        exact=0.4710,
        link_acc=0.9065,
        severity_per_gold=3.0639,
        hdfp_per_row=0.2439,
    ),
    AblationRow(
        name="degree-depth-random risk-aware near123",
        threshold=0.05,
        positive_rate=0.3498,
        f1=0.6426,
        exact=0.4708,
        link_acc=0.9140,
        severity_per_gold=3.0670,
        hdfp_per_row=0.2411,
    ),
    AblationRow(
        name="with ontology node features",
        threshold=0.05,
        positive_rate=None,
        f1=0.6436,
        exact=0.4713,
        link_acc=0.9133,
        severity_per_gold=3.0537,
        hdfp_per_row=0.2289,
    ),
)

DEFAULT_BOOTSTRAP_DELTAS: tuple[BootstrapDelta, ...] = (
    BootstrapDelta(
        variant="linker_vs_risk_scalar",
        f1=0.08994028909240104,
        exact=0.022272682801411592,
        link_acc=0.0006277884245995402,
        severity=-1.0590366023749338,
        hdfp=-0.3764982636944102,
        f1_ci=(0.08906992589429197, 0.09056924872563021),
        exact_ci=(0.021747195397014363, 0.022759248719408043),
        link_acc_ci=(0.00010036462134466184, 0.0011722300275477382),
        severity_ci=(-1.0661753150473396, -1.0501099370360611),
        hdfp_ci=(-0.3786445614428139, -0.3740159067995967),
    ),
    BootstrapDelta(
        variant="linker_vs_base_scalar",
        f1=0.09399952767814757,
        exact=0.014279636046752364,
        link_acc=0.003005696537656477,
        severity=-1.201002486877342,
        hdfp=-0.4506822000672118,
        f1_ci=(0.09335272671716255, 0.0946450672903788),
        exact_ci=(0.013847686819786653, 0.01468481048471737),
        link_acc_ci=(0.0025284063277124513, 0.003468313449595861),
        severity_ci=(-1.208488212463, -1.1920750261138107),
        hdfp_ci=(-0.4532765766774952, -0.4481774392293043),
    ),
)


def _as_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value))


def _as_float_optional(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _load_json_payload(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"source summary must be a JSON object: {path}")
    return payload


def _coerce_main_rows(payload: dict[str, Any]) -> list[dict[str, float]]:
    rows = payload.get("main_rows") or payload.get("main")
    if not isinstance(rows, list):
        return [r.__dict__.copy() for r in DEFAULT_MAIN_ROWS]
    out: list[dict[str, float]] = []
    by_name = {
        str(item.get("name")): item
        for item in rows
        if isinstance(item, dict) and item.get("name") is not None
    }
    required = [r.name for r in DEFAULT_MAIN_ROWS]
    for row in DEFAULT_MAIN_ROWS:
        source = by_name.get(row.name, {})
        if not isinstance(source, dict):
            source = {}
        out.append(
            {
                "name": row.name,
                "f1": _as_float(source.get("f1", source.get("F1", row.f1)), default=row.f1),
                "exact": _as_float(
                    source.get("exact", source.get("exact_set_match_rate", row.exact)),
                    default=row.exact,
                ),
                "link_acc": _as_float(
                    source.get("link_acc", source.get("link_accuracy", row.link_acc)),
                    default=row.link_acc,
                ),
                "severity_per_gold": _as_float(
                    source.get("severity_per_gold", source.get("mean_severity_per_gold", row.severity_per_gold)),
                    default=row.severity_per_gold,
                ),
                "hdfp_per_row": _as_float(
                    source.get("hdfp_per_row", source.get("high_distance_fp_per_row", row.hdfp_per_row)),
                    default=row.hdfp_per_row,
                ),
            }
        )
    # Preserve additional known rows if a richer source summary is supplied.
    extra_rows = [item for item in rows if isinstance(item, dict) and str(item.get("name")) not in required]
    for item in extra_rows:
        item_name = str(item["name"])
        out.append(
            {
                "name": item_name,
                "f1": _as_float(item.get("f1"), default=0.0),
                "exact": _as_float(item.get("exact", item.get("exact_set_match_rate")), default=0.0),
                "link_acc": _as_float(item.get("link_acc", item.get("link_accuracy")), default=0.0),
                "severity_per_gold": _as_float(
                    item.get("severity_per_gold", item.get("mean_severity_per_gold")),
                    default=0.0,
                ),
                "hdfp_per_row": _as_float(
                    item.get("hdfp_per_row", item.get("high_distance_fp_per_row")),
                    default=0.0,
                ),
            }
        )
    return out


def _coerce_ablation_rows(payload: dict[str, Any]) -> list[dict[str, float]]:
    rows = payload.get("ablation_rows")
    if not isinstance(rows, list) or not rows:
        return [r.__dict__.copy() for r in DEFAULT_ABLATION_ROWS]
    out: list[dict[str, float]] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        out.append(
            {
                "name": str(row["name"]),
                "threshold": _as_float_optional(row.get("threshold")),
                "positive_rate": _as_float_optional(row.get("positive_rate")),
                "f1": _as_float(row.get("f1", row.get("F1"))),
                "exact": _as_float(row.get("exact", row.get("exact_set_match_rate"))),
                "link_acc": _as_float(row.get("link_acc", row.get("link_accuracy"))),
                "severity_per_gold": _as_float(
                    row.get("severity_per_gold", row.get("mean_severity_per_gold")),
                ),
                "hdfp_per_row": _as_float(
                    row.get("hdfp_per_row", row.get("high_distance_fp_per_row")),
                ),
            }
        )
    return out


def _coerce_bootstrap_deltas(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("bootstrap_deltas") or payload.get("bootstrap")
    if not isinstance(rows, list) or not rows:
        return [r.__dict__.copy() for r in DEFAULT_BOOTSTRAP_DELTAS]
    out: list[dict[str, Any]] = []
    defaults = {r.variant: r for r in DEFAULT_BOOTSTRAP_DELTAS}
    for row in rows:
        if not isinstance(row, dict) or not row.get("variant"):
            continue
        variant = str(row["variant"])
        fallback = defaults.get(variant)
        out.append(
            {
                "variant": variant,
                "f1": _as_float(row.get("f1", row.get("delta_f1"),), default=fallback.f1 if fallback else 0.0),
                "exact": _as_float(
                    row.get("exact", row.get("delta_exact")),
                    default=fallback.exact if fallback else 0.0,
                ),
                "link_acc": _as_float(
                    row.get("link_acc", row.get("delta_link_acc")),
                    default=fallback.link_acc if fallback else 0.0,
                ),
                "severity": _as_float(
                    row.get("severity", row.get("delta_severity")),
                    default=fallback.severity if fallback else 0.0,
                ),
                "hdfp": _as_float(
                    row.get("hdfp", row.get("delta_hdfp", row.get("delta_hdfp_per_row"))),
                    default=fallback.hdfp if fallback else 0.0,
                ),
                "f1_ci": [
                    _as_float((row.get("f1_ci") or [None, None])[0], default=(fallback.f1_ci[0] if fallback else 0.0)),
                    _as_float((row.get("f1_ci") or [None, None])[1], default=(fallback.f1_ci[1] if fallback else 0.0)),
                ],
                "exact_ci": [
                    _as_float(
                        (row.get("exact_ci") or [None, None])[0],
                        default=(fallback.exact_ci[0] if fallback else 0.0),
                    ),
                    _as_float(
                        (row.get("exact_ci") or [None, None])[1],
                        default=(fallback.exact_ci[1] if fallback else 0.0),
                    ),
                ],
                "link_acc_ci": [
                    _as_float(
                        (row.get("link_acc_ci") or [None, None])[0],
                        default=(fallback.link_acc_ci[0] if fallback else 0.0),
                    ),
                    _as_float(
                        (row.get("link_acc_ci") or [None, None])[1],
                        default=(fallback.link_acc_ci[1] if fallback else 0.0),
                    ),
                ],
                "severity_ci": [
                    _as_float(
                        (row.get("severity_ci") or [None, None])[0],
                        default=(fallback.severity_ci[0] if fallback else 0.0),
                    ),
                    _as_float(
                        (row.get("severity_ci") or [None, None])[1],
                        default=(fallback.severity_ci[1] if fallback else 0.0),
                    ),
                ],
                "hdfp_ci": [
                    _as_float(
                        (row.get("hdfp_ci") or row.get("hdfp_per_row_ci") or [None, None])[0],
                        default=(fallback.hdfp_ci[0] if fallback else 0.0),
                    ),
                    _as_float(
                        (row.get("hdfp_ci") or row.get("hdfp_per_row_ci") or [None, None])[1],
                        default=(fallback.hdfp_ci[1] if fallback else 0.0),
                    ),
                ],
            }
        )
    return out


def _load_metrics(source_summary: Path | None) -> dict[str, list[dict[str, Any]]]:
    if source_summary is None:
        return {
            "main_rows": [r.__dict__.copy() for r in DEFAULT_MAIN_ROWS],
            "ablation_rows": [r.__dict__.copy() for r in DEFAULT_ABLATION_ROWS],
            "bootstrap_deltas": [r.__dict__.copy() for r in DEFAULT_BOOTSTRAP_DELTAS],
        }

    payload = _load_json_payload(source_summary)
    return {
        "main_rows": _coerce_main_rows(payload),
        "ablation_rows": _coerce_ablation_rows(payload),
        "bootstrap_deltas": _coerce_bootstrap_deltas(payload),
        "source_summary": source_summary.name,
    }


def _fmt_table_row(value: float | None, *, is_percent: bool = False, digits: int = 4) -> str:
    if value is None:
        return "--"
    if is_percent:
        return f"{value:.{digits}f}"
    return f"{value:.{digits}f}"


def _fmt_ci(values: list[float] | tuple[float, float]) -> str:
    return f"[{_fmt_table_row(values[0])}, {_fmt_table_row(values[1])}]"


def _main_table_lines(main_rows: list[dict[str, Any]], *, compact_headers: bool) -> list[str]:
    if compact_headers:
        header = "| Model | F1 | Exact | Link Acc | Severity/gold | HDFP/row |"
    else:
        header = "| Model | F1 | Exact | Link Acc | Severity per Gold | HDFP per Row |"
    lines = [header, "|---|---|---|---|---|---|"]
    for row in main_rows:
        lines.append(
            "| {name} | {f1} | {exact} | {link_acc} | {severity} | {hdfp} |".format(
                name=row["name"],
                f1=_fmt_table_row(row["f1"]),
                exact=_fmt_table_row(row["exact"]),
                link_acc=_fmt_table_row(row["link_acc"]),
                severity=_fmt_table_row(row["severity_per_gold"]),
                hdfp=_fmt_table_row(row["hdfp_per_row"]),
            )
        )
    return lines


def _bootstrap_table_lines(bootstrap_deltas: list[dict[str, Any]], *, compact_headers: bool) -> list[str]:
    if compact_headers:
        header = (
            "| Comparison | F1 delta | Exact delta | Link Acc delta | Severity delta | HDFP delta | "
            "F1 95% CI | Exact 95% CI | Link Acc 95% CI | Severity 95% CI | HDFP 95% CI |"
        )
    else:
        header = (
            "| Variant | F1 Δ | Exact Δ | Link Acc Δ | Severity Δ | HDFP Δ | "
            "F1 CI | Exact CI | Link Acc CI | Severity CI | HDFP CI |"
        )
    lines = [header, "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in bootstrap_deltas:
        lines.append(
            "| {variant} | {f1} | {exact} | {link_acc} | {severity} | {hdfp} |"
            " {f1_ci} | {exact_ci} | {link_acc_ci} | {severity_ci} | {hdfp_ci} |".format(
                variant=row["variant"],
                f1=_fmt_table_row(row["f1"]),
                exact=_fmt_table_row(row["exact"]),
                link_acc=_fmt_table_row(row["link_acc"]),
                severity=_fmt_table_row(row["severity"]),
                hdfp=_fmt_table_row(row["hdfp"]),
                f1_ci=_fmt_ci(row["f1_ci"]),
                exact_ci=_fmt_ci(row["exact_ci"]),
                link_acc_ci=_fmt_ci(row["link_acc_ci"]),
                severity_ci=_fmt_ci(row["severity_ci"]),
                hdfp_ci=_fmt_ci(row["hdfp_ci"]),
            )
        )
    return lines


def _ablation_table_lines(ablations: list[dict[str, Any]], *, compact_headers: bool) -> list[str]:
    if compact_headers:
        header = "| Variant | Threshold | Positive Rate | F1 | Exact | Link Acc | Severity/gold | HDFP/row |"
    else:
        header = "| Variant | Threshold | Positive Rate | F1 | Exact | Link Acc | Severity per Gold | HDFP per Row |"
    lines = [header, "|---|---|---|---|---|---|---|---|"]
    for row in ablations:
        lines.append(
            "| {name} | {threshold} | {positive_rate} | {f1} | {exact} | {link_acc} | {severity} | {hdfp} |".format(
                name=row["name"],
                threshold=_fmt_table_row(row["threshold"]),
                positive_rate="--" if row["positive_rate"] is None else _fmt_table_row(row["positive_rate"]),
                f1=_fmt_table_row(row["f1"]),
                exact=_fmt_table_row(row["exact"]),
                link_acc=_fmt_table_row(row["link_acc"]),
                severity=_fmt_table_row(row["severity_per_gold"]),
                hdfp=_fmt_table_row(row["hdfp_per_row"]),
            )
        )
    return lines


def _write_performance_markdown(output: Path, main_rows: list[dict[str, Any]], bootstrap_deltas: list[dict[str, Any]], ablations: list[dict[str, Any]]) -> None:
    lines = [
        f"# {MODEL_NAME} Performance",
        "",
        "## Main Evaluation Rows",
        "",
        *_main_table_lines(main_rows, compact_headers=False),
    ]

    lines.extend(
        [
            "",
            "## Bootstrap Deltas",
            "",
            *_bootstrap_table_lines(bootstrap_deltas, compact_headers=False),
        ]
    )

    lines.extend(
        [
            "",
            "## Ablation Rows",
            "",
            *_ablation_table_lines(ablations, compact_headers=False),
        ]
    )

    lines.extend(
        [
            "",
            "## Scope",
            "",
            "- Severe-error/high-distance false-positive risk control focus.",
            "- No deployment-ready claim is made.",
            "- This release does not contain row-level predictions.",
        "- Concept-memory bundle is not redistributed in this public package.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_model_card(output: Path) -> None:
    lines = [
        f"# {MODEL_NAME}",
        "",
        "## Model Card",
        "",
        "- **Task**: Clinical concept linking risk-control and false-positive suppression.",
        "- **Model family**: Re-ranking model with risk-aware calibration.",
        "- **Scope**: Public release of aggregate metrics and reproducible packaging metadata.",
        "",
        "## Intended Use",
        "",
        "- Reduce severe-error / high-distance false positives.",
        "- Compare with risk-aware references under equivalent candidate generation and evaluation setup.",
        "",
        "## Claim Boundary",
        "",
        "- This is a **severe-error/high-distance false-positive risk-control model**.",
        "- This package does **not** claim clinical validation.",
        "- This package does **not** claim production deployment readiness.",
        "- This package does **not** claim state-of-the-art status.",
        "- Concept memory bundle is regeneration-required unless redistribution is permitted by the controlling ontology license.",
        "",
        "## Public Outputs",
        "",
        "- `performance_tables.md`",
        "- `performance_tables.json`",
        f"- `release/{RELEASE_ID}/manifest.json`",
        "- Public figures when source assets are available.",
        "",
        "## Non-goals in this public pack",
        "",
        "- No row-level prediction dumps.",
        "- No restricted training data or local absolute paths.",
        "- No internal version tags in public text.",
        "",
        "## Citation",
        "",
        "If you use this public material, cite the original corresponding publication and follow the data usage terms of the underlying resources.",
        "",
        "## License and Source Terms",
        "",
        "- Repository code, documentation, tests, release scripts, and public aggregate metadata: MIT License, https://opensource.org/license/mit.",
        "- Packaged checkpoint and config: public research artifacts in this repository; no row-level predictions, training rows, clinical text, patient/document identifiers, mention offsets, or concept-memory bundle are included.",
        "- MIMIC-IV-Note: https://physionet.org/content/mimic-iv-note/",
        "- PhysioNet credentialed access and data-use terms: https://physionet.org/content/mimiciv/view-dua/1.0/",
        "- OMOP Common Data Model: https://www.ohdsi.org/data-standardization/the-common-data-model/",
        "- OHDSI Athena vocabulary access: https://athena.ohdsi.org/",
        "- MedCAT: https://github.com/CogStack/MedCAT",
        "",
        "## Contact",
        "",
        "Please route requests through the repository’s issue tracker or release notes for the public project.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_checkpoint_config(path: Path) -> None:
    payload = {
        "public_model_name": MODEL_NAME,
        "release_id": RELEASE_ID,
        "architecture": "SapBERT full-memory span-lattice pair-MLP accept scorer",
        "decision_threshold": DECISION_THRESHOLD,
        "task": "severe-error and high-distance false-positive risk control",
        "concept_memory": {
            "status": "regeneration_required",
            "redistribution": "not_included_without_license_confirmation",
        },
        "row_level_predictions": "not_included",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _checkpoint_entry(release_dir: Path, checkpoint: Path | None) -> dict[str, Any]:
    config_path = release_dir / CHECKPOINT_CONFIG_NAME
    _write_checkpoint_config(config_path)
    config_entry = {
        "status": "packaged",
        "filename": CHECKPOINT_CONFIG_NAME,
        "bytes": config_path.stat().st_size,
        "sha256": _sha256(config_path),
    }

    if checkpoint is None:
        return {
            "status": "not_packaged",
            "reason": "No checkpoint path supplied for this release.",
            "filename": CHECKPOINT_SANITIZED_NAME,
            "config": config_entry,
        }

    if not checkpoint.exists():
        return {
            "status": "not_packaged",
            "reason": "Checkpoint source was not available.",
            "filename": CHECKPOINT_SANITIZED_NAME,
            "config": config_entry,
        }

    packaged_checkpoint = release_dir / CHECKPOINT_SANITIZED_NAME
    if not packaged_checkpoint.exists() or checkpoint.resolve() != packaged_checkpoint.resolve():
        shutil.copy2(checkpoint, packaged_checkpoint)
    checkpoint_entry: dict[str, Any] = {
        "status": "packaged",
        "filename": CHECKPOINT_SANITIZED_NAME,
        "bytes": packaged_checkpoint.stat().st_size,
        "sha256": _sha256(packaged_checkpoint),
        "config": config_entry,
    }
    return checkpoint_entry


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and source.resolve() == destination.resolve():
        return True
    shutil.copy2(source, destination)
    return True


def _collect_figure_status(
    root: Path,
    source_dir: Path,
    explicit_sources: dict[str, Path | None],
) -> tuple[dict[str, Any], list[str], list[str]]:
    figure_dir = root / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    source_name_map: dict[str, str] = {
        OVERVIEW_FIGURE_PNG: "overview",
        OVERVIEW_FIGURE_PDF: "overview",
        "risk_control_pipeline.png": "pipeline",
        "risk_control_pipeline.pdf": "pipeline",
        "risk_frontier.png": "frontier",
        "risk_frontier.pdf": "frontier",
    }

    result: dict[str, Any] = {}
    missing: list[str] = []
    included: list[str] = []

    for output_name, variant in source_name_map.items():
        source_path = explicit_sources.get(output_name) or source_dir / output_name

        copied = _copy_if_exists(source_path, figure_dir / output_name)
        result[output_name] = {
            "status": "included" if copied else "missing",
            "destination": f"docs/public_release/figures/{output_name}",
            "variant": variant,
        }
        if copied:
            copied_path = figure_dir / output_name
            result[output_name]["bytes"] = copied_path.stat().st_size
            result[output_name]["sha256"] = _sha256(copied_path)
        if copied:
            included.append(output_name)
        else:
            missing.append(output_name)

    return result, missing, included


def _write_release_readme(output: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# HOVE Risk-Control Linker Release",
        "",
        f"Model name: `{MODEL_NAME}`",
        f"Release package id: `{RELEASE_ID}`",
        "",
        "## What is included",
        "",
        "- Public model card",
        "- Performance tables in Markdown and JSON",
        "- Publicly safe manifest",
        "- Optional figures (only if source figures are available)",
        "- Root `NOTICE`, `LICENSE`, and `requirements.txt` files",
        "",
        "## Integrity",
        "",
        f"- Checkpoint status: `{manifest['checkpoint']['status']}`",
        f"- Checkpoint filename: `{manifest['checkpoint']['filename']}`",
        "- No row-level prediction file dumps are included.",
        "- Concept-memory bundle is not included in this public release.",
        "",
        "## Notes",
        "",
        "Only aggregate model metrics are provided for public sharing. Any training or",
        "dataset-level material is intentionally out of scope.",
        "",
        "License and upstream-resource boundaries are documented in the repository",
        "root `README.md`, `NOTICE`, and `LICENSE` files.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_repository_readme(
    output: Path,
    metrics: dict[str, list[dict[str, Any]]],
) -> None:
    lines = [
        f"# {MODEL_NAME}",
        "",
        "**A research checkpoint and reproducibility package for risk-controlled",
        "clinical concept linking.** HOVE Risk-Control Linker focuses on reducing",
        "severe-error and high-distance false positives while preserving aggregate",
        "linking quality. This repository is structured as a public model-release",
        "artifact, not as a clinical deployment package.",
        "",
        "![HOVE Risk-Control Linker overview](docs/public_release/figures/hove_risk_control_linker_overview.png)",
        "",
        "## At a Glance",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Release type | Packaged research checkpoint, public config, model card, figures, and aggregate evaluation artifacts |",
        "| Task | Candidate acceptance/deferral for clinical concept linking |",
        "| Primary risk target | Severe-error and high-distance false-positive control |",
        "| Public evidence | Main evaluation table, bootstrap deltas, ablations, figure hashes, and manifest hashes |",
        "| Public data boundary | Aggregate metrics only; no row-level predictions, clinical text, or patient/document identifiers |",
        "| License | MIT for repository code, documentation, tests, release scripts, and public aggregate metadata |",
        "",
        "## Purpose",
        "",
        "HOVE Risk-Control Linker makes the public, auditable portion of a",
        "clinical concept-linking risk-control model available without exposing",
        "restricted row-level artifacts. The release packages enough information to",
        "inspect the model boundary, verify artifact integrity, compare aggregate",
        "results, and reproduce the public manifest.",
        "",
        "The model is scoped to selective risk control: it accepts candidate links",
        "when the risk-control score clears the public threshold and abstains when",
        "the candidate is more likely to create a severe-error or high-distance",
        "false positive. The release is designed for research comparison and",
        "artifact review, not bedside use or production clinical deployment.",
        "",
        "Example uses:",
        "",
        "- Verify the packaged checkpoint/config hashes and reproduce the public",
        "  aggregate manifest before citing or redistributing the release.",
        "- Compare a new concept-linking risk-control method against the included",
        "  aggregate baselines and bootstrap deltas.",
        "- Inspect the risk frontier to understand the F1 versus high-distance",
        "  false-positive tradeoff at the selected public operating point.",
        "- Use the model card and claim boundary as a template for publishing a",
        "  clinical NLP checkpoint without row-level prediction dumps or clinical",
        "  text.",
        "- Audit a release branch to ensure private paths, internal version labels,",
        "  prediction JSONL files, patient/document identifiers, and concept-memory",
        "  bundles are not committed.",
        "",
        "## Repository Layout",
        "",
        "| Path | Purpose |",
        "|---|---|",
        "| `release/hove-risk-control-linker/` | Packaged checkpoint, public config, release README, and manifest |",
        "| `docs/public_release/model_card.md` | Model scope, claim boundary, intended use, and exclusions |",
        "| `docs/public_release/performance_tables.md` | Human-readable aggregate evaluation tables |",
        "| `docs/public_release/performance_tables.json` | Machine-readable performance source of truth |",
        "| `docs/public_release/figures/` | Public overview, pipeline, and risk-frontier figures |",
        "| `scripts/make_hove_risk_control_release.py` | Regenerates public metadata and README tables |",
        "| `scripts/audit_public_release.py` | Guards against internal labels, private paths, and row-level artifacts |",
        "| `tests/` | Release-regression and public-audit tests |",
        "",
        "The repository intentionally excludes row-level predictions, clinical text,",
        "training/dev/test rows, patient or document identifiers, and the",
        "concept-memory bundle.",
        "",
        "## Requirements",
        "",
        "The public release checks are tested with Python 3.11. `requirements.txt`",
        "includes the public audit dependencies and the broader HOVE-style runtime",
        "needed to load the packaged checkpoint and build training/inference adapters.",
        "",
        "```text",
        "pytest==9.0.3",
        "numpy==2.1.2",
        "pandas==2.3.3",
        "scipy==1.15.3",
        "scikit-learn==1.7.2",
        "torch==2.10.0",
        "transformers==5.5.4",
        "sentence-transformers==5.1.2",
        "```",
        "",
        "The included checkpoint is a packaged research artifact. This repository's",
        "public tests verify hashes, manifests, tables, figures, and leak guards;",
        "they do not require private datasets or concept-memory artifacts.",
        "",
        "## Quick Start",
        "",
        "Clone the repository and install the pinned environment:",
        "",
        "```bash",
        "python3 -m venv .venv",
        ". .venv/bin/activate",
        "python -m pip install -U pip",
        "python -m pip install -r requirements.txt",
        "```",
        "",
        "Verify the public package before citing, modifying, or redistributing it:",
        "",
        "```bash",
        "python3 scripts/audit_public_release.py --allow-doc-local-paths --require-risk-control-release",
        "python3 -m pytest tests/test_public_release_audit.py tests/test_hove_risk_control_release.py -q",
        "python3 -m json.tool docs/public_release/performance_tables.json >/dev/null",
        "python3 -m json.tool release/hove-risk-control-linker/manifest.json >/dev/null",
        "python3 -m json.tool release/hove-risk-control-linker/risk_control_linker_config.json >/dev/null",
        "```",
        "",
        "Regenerate the public release metadata after changing source metrics,",
        "figures, or packaged checkpoint artifacts:",
        "",
        "```bash",
        "python3 scripts/make_hove_risk_control_release.py \\",
        "  --checkpoint release/hove-risk-control-linker/risk_control_linker.pt",
        "```",
        "",
        "## Model Package",
        "",
        "```text",
        "release/hove-risk-control-linker/risk_control_linker.pt",
        "release/hove-risk-control-linker/risk_control_linker_config.json",
        "release/hove-risk-control-linker/manifest.json",
        "```",
        "",
        "The manifest records packaged public artifacts, figure hashes, checkpoint",
        "hashes, and the explicit exclusion of row-level prediction files.",
        "",
        "## Evaluation Snapshot",
        "",
        *_main_table_lines(metrics["main_rows"], compact_headers=True),
        "",
        "Lower `Severity/gold` and `HDFP/row` indicate lower severe-error and",
        "high-distance false-positive risk under the public evaluation summary.",
        "",
        "![Risk-control frontier](docs/public_release/figures/risk_frontier.png)",
        "",
        "## Statistical Comparison",
        "",
        *_bootstrap_table_lines(metrics["bootstrap_deltas"], compact_headers=True),
        "",
        "Negative severity and HDFP deltas mean the linker reduces those risk metrics",
        "relative to the comparison reference.",
        "",
        "## Ablations",
        "",
        *_ablation_table_lines(metrics["ablation_rows"], compact_headers=True),
        "",
        "## Release Boundary",
        "",
        "This repository does not redistribute dataset rows, clinical text, note IDs,",
        "subject IDs, admission IDs, mention offsets, or row-level prediction dumps.",
        "Silver dataset regeneration material is maintained separately as",
        "`clinical-ontology-embeddings/omop-medcat-silver`.",
        "",
        "The public package also excludes the concept-memory bundle until its",
        "license boundary is reviewed separately.",
        "",
        "## Claim Boundary",
        "",
        "This release is limited to severe-error and high-distance false-positive",
        "risk control for clinical concept linking. It does not claim clinical",
        "validation, deployment readiness, or state-of-the-art biomedical entity",
        "linking performance.",
        "",
        "## Acknowledgements",
        "",
        ACKNOWLEDGEMENT_TEXT,
        "",
        "## Citation",
        "",
        "If you use this package, cite the corresponding publication and follow the",
        "data usage terms for all upstream clinical and ontology resources.",
        "",
        "## License and External Terms",
        "",
        "Repository code, documentation, tests, release scripts, and public aggregate",
        "metadata are distributed under the [MIT License](LICENSE). The MIT license",
        "text is also available from the Open Source Initiative:",
        "https://opensource.org/license/mit.",
        "",
        "The packaged checkpoint and config are released as public research artifacts",
        "in this repository. They do not include row-level predictions, training",
        "rows, clinical text, patient identifiers, document identifiers, mention",
        "offsets, or the concept-memory bundle.",
        "",
        "External resources remain governed by their own terms:",
        "",
        "- MIMIC-IV-Note: https://physionet.org/content/mimic-iv-note/",
        "- PhysioNet credentialed access and data-use terms: https://physionet.org/content/mimiciv/view-dua/1.0/",
        "- OMOP Common Data Model: https://www.ohdsi.org/data-standardization/the-common-data-model/",
        "- OHDSI Athena vocabulary access: https://athena.ohdsi.org/",
        "- MedCAT: https://github.com/CogStack/MedCAT",
        "- Recipe-only silver dataset companion: https://github.com/clinical-ontology-embeddings/omop-medcat-silver",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_performance_json(
    output: Path,
    metrics: dict[str, list[dict[str, Any]]],
) -> None:
    payload = {
        "public_model_name": MODEL_NAME,
        "release_id": RELEASE_ID,
        "main_rows": metrics["main_rows"],
        "bootstrap_deltas": metrics["bootstrap_deltas"],
        "ablation_rows": metrics["ablation_rows"],
    }
    if "source_summary" in metrics:
        payload["source_summary"] = metrics["source_summary"]
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate public release artifacts for HOVE Risk-Control Linker."
    )
    parser.add_argument("--source-summary", type=Path, help="Optional metric source summary JSON.")
    parser.add_argument(
        "--output-docs",
        type=Path,
        default=Path("docs/public_release"),
        help="Output directory for public markdown/json outputs.",
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=Path(f"release/{RELEASE_ID}"),
        help="Release artifact directory.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Optional source checkpoint path.",
    )
    parser.add_argument(
        "--figure-source-dir",
        type=Path,
        default=Path("docs/public_release/figures"),
        help="Directory containing source figure files.",
    )
    parser.add_argument("--pipeline-figure-png", type=Path, default=None)
    parser.add_argument("--pipeline-figure-pdf", type=Path, default=None)
    parser.add_argument("--frontier-figure-png", type=Path, default=None)
    parser.add_argument("--frontier-figure-pdf", type=Path, default=None)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root path for relative input/output resolution.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output_docs = (root / args.output_docs).resolve()
    release_dir = (root / args.release_dir).resolve()
    fig_source = root / args.figure_source_dir
    if not fig_source.exists():
        fig_source = root / args.figure_source_dir

    source_summary = args.source_summary
    if source_summary is not None:
        source_summary = source_summary if source_summary.is_absolute() else root / source_summary
    checkpoint = args.checkpoint
    if checkpoint is not None and not checkpoint.is_absolute():
        checkpoint = root / checkpoint

    explicit_figure_sources = {
        "risk_control_pipeline.png": args.pipeline_figure_png,
        "risk_control_pipeline.pdf": args.pipeline_figure_pdf,
        "risk_frontier.png": args.frontier_figure_png,
        "risk_frontier.pdf": args.frontier_figure_pdf,
    }
    explicit_figure_sources = {
        output_name: source if source is None or source.is_absolute() else root / source
        for output_name, source in explicit_figure_sources.items()
    }

    metrics = _load_metrics(source_summary if source_summary and source_summary.exists() else None)
    output_docs.mkdir(parents=True, exist_ok=True)
    figures_dir = output_docs / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    _write_model_card(output_docs / "model_card.md")
    _write_performance_markdown(output_docs / "performance_tables.md", metrics["main_rows"], metrics["bootstrap_deltas"], metrics["ablation_rows"])
    _write_performance_json(output_docs / "performance_tables.json", metrics)
    _write_repository_readme(root / "README.md", metrics)

    figure_status, missing_figures, included_figures = _collect_figure_status(
        output_docs,
        fig_source,
        explicit_figure_sources,
    )

    release_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "public_model_name": MODEL_NAME,
        "release_id": RELEASE_ID,
        "public_files": {
            "model_card": "docs/public_release/model_card.md",
            "performance_tables_md": "docs/public_release/performance_tables.md",
            "performance_tables_json": "docs/public_release/performance_tables.json",
            "checkpoint_config": f"release/{RELEASE_ID}/{CHECKPOINT_CONFIG_NAME}",
        },
        "figures": figure_status,
        "checkpoint": _checkpoint_entry(release_dir, checkpoint),
        "concept_memory": {
            "status": "excluded",
            "reason": "Concept-memory bundle is not included in the public package.",
            "allowed": [],
        },
        "row_level_predictions": {
            "status": "excluded",
            "reason": "No row-level prediction files are included.",
        },
        "figure_report": {
            "expected": {
                "included": included_figures,
                "missing": missing_figures,
            }
        },
    }
    if "source_summary" in metrics:
        manifest["source_summary"] = metrics["source_summary"]
    (release_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_release_readme(release_dir / "README.md", manifest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
