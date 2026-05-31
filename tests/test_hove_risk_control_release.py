import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_hove_risk_control_release.py"
RELEASE_ID = "hove-risk-control-linker"
MODEL_NAME = "HOVE Risk-Control Linker"
OVERVIEW_PNG = "hove_risk_control_linker_overview.png"
OVERVIEW_PDF = "hove_risk_control_linker_overview.pdf"


def _fmt(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.4f}"


def _fmt_ci(values: list[float]) -> str:
    return f"[{_fmt(values[0])}, {_fmt(values[1])}]"


def _run_generator(root: Path, *, extra_args: list[str] | None = None) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(root),
        "--output-docs",
        "docs/public_release",
        "--release-dir",
        f"release/{RELEASE_ID}",
        "--figure-source-dir",
        "docs/paper/figures",
    ]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"generator failed (code {result.returncode}): {result.stdout}\n{result.stderr}"
        )


def _run_generator_with_defaults(root: Path, *, extra_args: list[str] | None = None) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(root),
    ]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(root),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"generator failed (code {result.returncode}): {result.stdout}\n{result.stderr}"
        )


def _read_text(*paths: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in paths)


def _write_source_summary(path: Path) -> None:
    payload = {
        "main_rows": [
            {
                "name": "unfiltered top3",
                "f1": 0.4310,
                "exact": 0.4840,
                "link_acc": 0.9007,
                "severity_per_gold": 7.3207,
                "hdfp_per_row": 1.9527,
            }
        ],
        "bootstrap_deltas": [
            {
                "variant": "linker_vs_risk_scalar",
                "f1": 0.08994028909240104,
                "exact": 0.022272682801411592,
                "link_acc": 0.0006277884245995402,
                "severity": -1.0590366023749338,
                "hdfp": -0.3764982636944102,
                "f1_ci": [0.08906992589429197, 0.09056924872563021],
                "exact_ci": [0.021747195397014363, 0.022759248719408043],
                "link_acc_ci": [0.00010036462134466184, 0.0011722300275477382],
                "severity_ci": [-1.0661753150473396, -1.0501099370360611],
                "hdfp_ci": [-0.3786445614428139, -0.3740159067995967],
            }
        ],
        "ablation_rows": [
            {
                "name": "final true risk-aware near123",
                "threshold": 0.45,
                "positive_rate": 0.3487,
                "f1": 0.6660,
                "exact": 0.4794,
                "link_acc": 0.9119,
                "severity_per_gold": 2.8358,
                "hdfp_per_row": 0.1610,
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_figure_assets(root: Path) -> None:
    source_dir = root / "docs" / "paper" / "figures"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / OVERVIEW_PNG).write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\x88D\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (source_dir / OVERVIEW_PDF).write_bytes(b"%PDF-1.4\n% public overview placeholder\n")
    for filename in [
        "risk_control_pipeline.png",
        "risk_control_pipeline.pdf",
        "risk_frontier.png",
        "risk_frontier.pdf",
    ]:
        (source_dir / filename).write_text(f"dummy {filename}", encoding="utf-8")


def test_generator_writes_expected_public_files(tmp_path: Path) -> None:
    root = tmp_path
    _write_source_summary(root / "source_summary.json")
    _write_figure_assets(root)
    _run_generator(
        root,
        extra_args=["--source-summary", "source_summary.json"],
    )

    docs_dir = root / "docs" / "public_release"
    release_dir = root / "release" / RELEASE_ID
    assert (docs_dir / "model_card.md").exists()
    assert (docs_dir / "performance_tables.md").exists()
    assert (docs_dir / "performance_tables.json").exists()
    assert (docs_dir / "figures" / OVERVIEW_PNG).exists()
    assert (docs_dir / "figures" / OVERVIEW_PDF).exists()
    assert (docs_dir / "figures" / "risk_control_pipeline.png").exists()
    assert (docs_dir / "figures" / "risk_control_pipeline.pdf").exists()
    assert (docs_dir / "figures" / "risk_frontier.png").exists()
    assert (docs_dir / "figures" / "risk_frontier.pdf").exists()
    assert (release_dir / "manifest.json").exists()
    assert (release_dir / "README.md").exists()


def test_generator_writes_paper_style_readme_with_inline_performance_tables(tmp_path: Path) -> None:
    root = tmp_path
    _write_figure_assets(root)
    _run_generator(root)

    readme = (root / "README.md").read_text(encoding="utf-8")
    payload = json.loads((root / "docs" / "public_release" / "performance_tables.json").read_text(encoding="utf-8"))

    assert "# HOVE Risk-Control Linker" in readme
    assert "![HOVE Risk-Control Linker overview](docs/public_release/figures/hove_risk_control_linker_overview.png)" in readme
    assert "![Risk-control frontier](docs/public_release/figures/risk_frontier.png)" in readme
    assert "## At a Glance" in readme
    assert "## Purpose" in readme
    assert "Example uses:" in readme
    assert "## Repository Layout" in readme
    assert "## Requirements" in readme
    assert "## Quick Start" in readme
    assert "## Evaluation Snapshot" in readme
    assert "## Release Boundary" in readme
    assert "pytest==9.0.3" in readme
    assert "| Model | F1 | Exact | Link Acc | Severity/gold | HDFP/row |" in readme
    assert "| Comparison | F1 delta | Exact delta | Link Acc delta | Severity delta | HDFP delta | F1 95% CI | Exact 95% CI | Link Acc 95% CI | Severity 95% CI | HDFP 95% CI |" in readme
    assert "| Variant | Threshold | Positive Rate | F1 | Exact | Link Acc | Severity/gold | HDFP/row |" in readme

    main_rows = {row["name"]: row for row in payload["main_rows"]}
    linker = main_rows[MODEL_NAME]
    assert (
        f"| {MODEL_NAME} | {_fmt(linker['f1'])} | {_fmt(linker['exact'])} | "
        f"{_fmt(linker['link_acc'])} | {_fmt(linker['severity_per_gold'])} | "
        f"{_fmt(linker['hdfp_per_row'])} |"
    ) in readme

    assert "| HOVE Risk-Control Linker | 0.6660 | 0.4794 | 0.9119 | 2.8358 | 0.1610 |" in readme
    assert "## Acknowledgements" in readme
    assert (
        "This research was supported by the AI Computing Infrastructure Enhancement "
        "(GPU Rental Support) User Support Program funded by the Ministry of Science "
        "and ICT (MSIT), Republic of Korea (No. RQT-25-120164)."
    ) in readme
    assert "## License and External Terms" in readme
    assert "https://opensource.org/license/mit" in readme
    assert "https://physionet.org/content/mimic-iv-note/" in readme
    assert "https://physionet.org/content/mimiciv/view-dua/1.0/" in readme
    assert "https://www.ohdsi.org/data-standardization/the-common-data-model/" in readme
    assert "https://athena.ohdsi.org/" in readme
    assert "https://github.com/CogStack/MedCAT" in readme
    assert "https://github.com/clinical-ontology-embeddings/omop-medcat-silver" in readme

    for row in payload["bootstrap_deltas"]:
        expected = (
            f"| {row['variant']} | {_fmt(row['f1'])} | {_fmt(row['exact'])} | "
            f"{_fmt(row['link_acc'])} | {_fmt(row['severity'])} | {_fmt(row['hdfp'])} | "
            f"{_fmt_ci(row['f1_ci'])} | {_fmt_ci(row['exact_ci'])} | "
            f"{_fmt_ci(row['link_acc_ci'])} | {_fmt_ci(row['severity_ci'])} | "
            f"{_fmt_ci(row['hdfp_ci'])} |"
        )
        assert expected in readme


def test_repository_declares_public_test_dependency() -> None:
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    lines = {
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "pytest==9.0.3" in lines
    assert "numpy==2.1.2" in lines
    assert "pandas==2.3.3" in lines
    assert "scikit-learn==1.7.2" in lines
    assert "torch==2.10.0" in lines
    assert "transformers==5.5.4" in lines
    assert "sentence-transformers==5.1.2" in lines


def test_overview_figure_is_copied_and_recorded_in_manifest(tmp_path: Path) -> None:
    root = tmp_path
    _write_figure_assets(root)
    _run_generator(root)

    figure_dir = root / "docs" / "public_release" / "figures"
    manifest = json.loads((root / "release" / RELEASE_ID / "manifest.json").read_text(encoding="utf-8"))

    overview_png = figure_dir / OVERVIEW_PNG
    overview_pdf = figure_dir / OVERVIEW_PDF
    assert overview_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert overview_pdf.read_bytes().startswith(b"%PDF")
    assert manifest["figures"][OVERVIEW_PNG]["status"] == "included"
    assert manifest["figures"][OVERVIEW_PDF]["status"] == "included"


def test_performance_tables_json_values(tmp_path: Path) -> None:
    root = tmp_path
    _write_source_summary(root / "source_summary.json")
    _write_figure_assets(root)
    _run_generator(root, extra_args=["--source-summary", "source_summary.json"])

    payload = json.loads((root / "docs" / "public_release" / "performance_tables.json").read_text(encoding="utf-8"))

    assert payload["public_model_name"] == MODEL_NAME
    rows = {row["name"]: row for row in payload["main_rows"]}
    assert rows["unfiltered top3"]["f1"] == pytest.approx(0.4310, rel=1e-12, abs=1e-12)
    assert rows["HOVE Risk-Control Linker"]["f1"] == pytest.approx(
        0.6659730198280197, rel=1e-12, abs=1e-12
    )
    assert rows["HOVE Risk-Control Linker"]["hdfp_per_row"] == pytest.approx(
        0.16103954295956088, rel=1e-12, abs=1e-12
    )

    deltas = {row["variant"]: row for row in payload["bootstrap_deltas"]}
    assert "linker_vs_risk_scalar" in deltas
    assert deltas["linker_vs_risk_scalar"]["link_acc"] == pytest.approx(0.0006277884245995402, rel=1e-12, abs=1e-12)

    ablations = {row["name"]: row for row in payload["ablation_rows"]}
    assert ablations["final true risk-aware near123"]["threshold"] == pytest.approx(0.45)
    assert ablations["final true risk-aware near123"]["positive_rate"] == pytest.approx(0.3487)


def test_no_internal_or_prediction_artifacts_in_public_outputs(tmp_path: Path) -> None:
    root = tmp_path
    _write_figure_assets(root)
    _run_generator(root)
    docs_dir = root / "docs" / "public_release"
    release_dir = root / "release" / RELEASE_ID
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))

    forbidden = [
        "/home/",
        "v" + "502",
        "V" + "502",
        "note_id",
        "subject_id",
        "hadm_id",
        "prediction.jsonl",
    ]
    combined = "\n".join(
        [
            (docs_dir / "model_card.md").read_text(encoding="utf-8"),
            (docs_dir / "performance_tables.md").read_text(encoding="utf-8"),
            json.dumps(manifest),
        ]
    )
    for token in forbidden:
        assert token not in combined

    assert re.search(r"\.jsonl", json.dumps(manifest)) is None
    assert manifest["row_level_predictions"]["status"] == "excluded"
    assert manifest["row_level_predictions"]["reason"] == "No row-level prediction files are included."
    assert manifest["concept_memory"]["status"] == "excluded"
    assert "rows" not in manifest["concept_memory"].get("allowed", [])


def test_no_checkpoint_but_manifest_records_not_packaged(tmp_path: Path) -> None:
    root = tmp_path
    _run_generator(root)
    manifest = json.loads((root / "release" / RELEASE_ID / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["checkpoint"]["filename"] == "risk_control_linker.pt"
    assert manifest["checkpoint"]["status"] == "not_packaged"
    assert manifest["checkpoint"]["reason"] == "No checkpoint path supplied for this release."
    assert manifest["checkpoint"]["config"]["status"] == "packaged"
    assert (root / "release" / RELEASE_ID / "risk_control_linker_config.json").exists()


def test_checkpoint_is_copied_with_sanitized_name(tmp_path: Path) -> None:
    root = tmp_path
    source_checkpoint = root / "private_checkpoint.pt"
    source_checkpoint.write_bytes(b"checkpoint-bytes")

    _run_generator(root, extra_args=["--checkpoint", str(source_checkpoint)])

    release_dir = root / "release" / RELEASE_ID
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    packaged_checkpoint = release_dir / "risk_control_linker.pt"
    config = json.loads((release_dir / "risk_control_linker_config.json").read_text(encoding="utf-8"))

    assert packaged_checkpoint.read_bytes() == b"checkpoint-bytes"
    assert manifest["checkpoint"]["status"] == "packaged"
    assert manifest["checkpoint"]["filename"] == "risk_control_linker.pt"
    assert manifest["checkpoint"]["config"]["status"] == "packaged"
    assert config["decision_threshold"] == pytest.approx(0.45)
    assert config["public_model_name"] == MODEL_NAME


def test_default_regeneration_preserves_existing_public_figures(tmp_path: Path) -> None:
    root = tmp_path
    docs_figure_dir = root / "docs" / "public_release" / "figures"
    docs_figure_dir.mkdir(parents=True)
    (docs_figure_dir / OVERVIEW_PNG).write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\x88D\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (docs_figure_dir / OVERVIEW_PDF).write_bytes(b"%PDF-1.4\n% public overview placeholder\n")
    for filename in [
        "risk_control_pipeline.png",
        "risk_control_pipeline.pdf",
        "risk_frontier.png",
        "risk_frontier.pdf",
    ]:
        (docs_figure_dir / filename).write_text(f"public figure {filename}", encoding="utf-8")

    _run_generator_with_defaults(root)

    manifest = json.loads((root / "release" / RELEASE_ID / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["figure_report"]["expected"]["missing"] == []
    assert set(manifest["figure_report"]["expected"]["included"]) == {
        OVERVIEW_PNG,
        OVERVIEW_PDF,
        "risk_control_pipeline.png",
        "risk_control_pipeline.pdf",
        "risk_frontier.png",
        "risk_frontier.pdf",
    }


def test_explicit_figure_source_can_point_to_output_without_crashing(tmp_path: Path) -> None:
    root = tmp_path
    docs_figure_dir = root / "docs" / "public_release" / "figures"
    docs_figure_dir.mkdir(parents=True)
    (docs_figure_dir / OVERVIEW_PNG).write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
        b"\x00\x05\xfe\x02\xfeA\x88D\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (docs_figure_dir / OVERVIEW_PDF).write_bytes(b"%PDF-1.4\n% public overview placeholder\n")
    figure_args: list[str] = []
    for flag, filename in [
        ("--pipeline-figure-png", "risk_control_pipeline.png"),
        ("--pipeline-figure-pdf", "risk_control_pipeline.pdf"),
        ("--frontier-figure-png", "risk_frontier.png"),
        ("--frontier-figure-pdf", "risk_frontier.pdf"),
    ]:
        path = docs_figure_dir / filename
        path.write_text(f"public figure {filename}", encoding="utf-8")
        figure_args.extend([flag, str(path)])

    _run_generator_with_defaults(root, extra_args=figure_args)

    manifest = json.loads((root / "release" / RELEASE_ID / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["figure_report"]["expected"]["missing"] == []


def test_checkpoint_source_can_point_to_output_without_crashing(tmp_path: Path) -> None:
    root = tmp_path
    release_dir = root / "release" / RELEASE_ID
    release_dir.mkdir(parents=True)
    checkpoint = release_dir / "risk_control_linker.pt"
    checkpoint.write_bytes(b"checkpoint-bytes")

    _run_generator_with_defaults(root, extra_args=["--checkpoint", str(checkpoint)])

    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["checkpoint"]["status"] == "packaged"
    assert checkpoint.read_bytes() == b"checkpoint-bytes"


def test_missing_figures_are_reported(tmp_path: Path) -> None:
    root = tmp_path
    _run_generator(root)
    manifest = json.loads((root / "release" / RELEASE_ID / "manifest.json").read_text(encoding="utf-8"))

    missing = manifest["figure_report"]["expected"]["missing"]
    assert set(missing) == {
        OVERVIEW_PNG,
        OVERVIEW_PDF,
        "risk_control_pipeline.png",
        "risk_control_pipeline.pdf",
        "risk_frontier.png",
        "risk_frontier.pdf",
    }
    assert manifest["figures"]["risk_frontier.png"]["status"] == "missing"
    assert not (root / "docs" / "public_release" / "figures" / "risk_frontier.png").exists()
