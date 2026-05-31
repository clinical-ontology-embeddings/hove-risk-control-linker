#!/usr/bin/env python3
"""Lightweight public-release audit for tracked repository files."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import re
import sys
from typing import Dict, List, Tuple


PUBLIC_MODEL_NAME = "HOVE Risk-Control Linker"
RISK_CONTROL_RELEASE_REQUIRED_FILES = (
    "NOTICE",
    "requirements.txt",
    "scripts/make_hove_risk_control_release.py",
    "docs/public_release/model_card.md",
    "docs/public_release/performance_tables.md",
    "docs/public_release/performance_tables.json",
    "docs/public_release/figures/hove_risk_control_linker_overview.png",
    "docs/public_release/figures/hove_risk_control_linker_overview.pdf",
    "docs/public_release/figures/risk_control_pipeline.png",
    "docs/public_release/figures/risk_control_pipeline.pdf",
    "docs/public_release/figures/risk_frontier.png",
    "docs/public_release/figures/risk_frontier.pdf",
    "release/hove-risk-control-linker/manifest.json",
    "release/hove-risk-control-linker/risk_control_linker_config.json",
    "release/hove-risk-control-linker/risk_control_linker.pt",
)
RISK_CONTROL_RELEASE_SCAN_PREFIXES = (
    "docs/public_release/",
    "release/hove-risk-control-linker/",
)
RISK_CONTROL_RELEASE_SCAN_FILES = (
    "README.md",
    "scripts/make_hove_risk_control_release.py",
)

BANNED_ROOT_PREFIXES = (
    "data",
    "experiments",
    "archive",
    "models",
    "wandb",
    "lightning_logs",
    "logs",
    "physionet.org",
    ".env",
    ".env.",
    ".agents",
    ".codex",
    ".moai",
    ".claude/local",
    "todolist",
    "third_party",
    "third_party/dbt_mimic_omop",
    "third_party/ohdsi_mimic",
    "third_party/hgcn",
    "third_party/hyperbolic_cones",
    "third_party/shadow_cones",
    "third_party/disk_embedding",
)

def _local_home_pattern() -> str:
    return "/".join(["", "home", "user", ""])


def _forbidden_text_patterns() -> Tuple[Tuple[str, re.Pattern[str]], ...]:
    return (
        ("home_user_path", re.compile(re.escape(_local_home_pattern()))),
        ("begin_private_key", re.compile("BEGIN " + "PRIVATE KEY")),
        ("aws_secret_access_key", re.compile("AWS" + "_SECRET_ACCESS_KEY")),
        ("authorization_bearer", re.compile("Authorization:" + " Bearer")),
        ("api_key", re.compile("api_" + "key=")),
        ("secret_key", re.compile("secret" + "-key")),
    )


FORBIDDEN_TEXT_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = _forbidden_text_patterns()

ALLOWED_PATTERN_OCCURRENCES: Tuple[Tuple[str, str], ...] = (
    (".gitignore", "secret_key"),
)

DOCS_TEXT_SKIP_PATTERNS = (
    re.compile(r"^docs/.*\.(zip|tar\.gz|tgz|gz)$", re.IGNORECASE),
)


def _run_git(command: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *command],
        capture_output=True,
        text=True,
        check=False,
    )


def _repo_root(start: Path) -> Path:
    result = _run_git(["rev-parse", "--show-toplevel"], start)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "not a git repository")
    return Path(result.stdout.strip())


def _is_banned_path(path: str) -> bool:
    if path.startswith(".env."):
        return True
    for prefix in BANNED_ROOT_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return True
    return False


def _is_docs_archive(path: str) -> bool:
    return any(pattern.match(path) for pattern in DOCS_TEXT_SKIP_PATTERNS)


def _is_risk_control_release_path(path: str) -> bool:
    return path in RISK_CONTROL_RELEASE_SCAN_FILES or any(
        path.startswith(prefix) for prefix in RISK_CONTROL_RELEASE_SCAN_PREFIXES
    )


def _risk_control_forbidden_patterns() -> Tuple[Tuple[str, re.Pattern[str]], ...]:
    return (
        ("internal_version", re.compile(r"\b[Vv]\d{3}\b")),
        ("home_user_path", re.compile(re.escape(_local_home_pattern()))),
        ("prediction_jsonl", re.compile(r"(?:dev|test|train|filtered|scored)[A-Za-z0-9_-]*predictions?\.jsonl")),
        ("row_note_id", re.compile(r"\bnote_id\b")),
        ("row_subject_id", re.compile(r"\bsubject_id\b")),
        ("row_hadm_id", re.compile(r"\bhadm_id\b")),
    )


RISK_CONTROL_FORBIDDEN_TEXT_PATTERNS = _risk_control_forbidden_patterns()


def _tracked_file_set(repo_root: Path) -> set[str]:
    tracked_result = _run_git(["ls-files", "-z"], repo_root)
    if tracked_result.returncode != 0 or not tracked_result.stdout:
        return set()
    return {path for path in tracked_result.stdout.split("\0") if path}


def _is_probably_text(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if not data:
        return False
    if b"\x00" in data:
        return False
    return True


def _decoded_file_text(path: Path) -> str:
    data = path.read_bytes()
    if not data:
        return ""
    if b"\x00" in data:
        printable_runs = re.findall(rb"[\x20-\x7e]{4,}", data)
        return "\n".join(run.decode("utf-8", errors="ignore") for run in printable_runs)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")


def _scan_file(
    repo_root: Path,
    relative_path: str,
    allow_doc_local_paths: bool,
) -> List[Dict[str, str]]:
    if _is_docs_archive(relative_path):
        return []

    absolute_path = repo_root / relative_path
    if not _is_probably_text(absolute_path):
        return []

    text = _decoded_file_text(absolute_path)

    errors: List[Dict[str, str]] = []
    for pattern_name, pattern in FORBIDDEN_TEXT_PATTERNS:
        if (relative_path, pattern_name) in ALLOWED_PATTERN_OCCURRENCES:
            continue
        if pattern_name == "home_user_path":
            if allow_doc_local_paths and relative_path.startswith("docs/"):
                continue
        if pattern.search(text):
            errors.append(
                {
                    "kind": "forbidden_pattern",
                    "file": relative_path,
                    "pattern": pattern.pattern,
                    "message": f"Found forbidden pattern '{pattern_name}' in tracked file.",
                }
            )
    return errors


def _scan_risk_control_release_file(repo_root: Path, relative_path: str) -> List[Dict[str, str]]:
    if not _is_risk_control_release_path(relative_path):
        return []
    if _is_docs_archive(relative_path):
        return []

    absolute_path = repo_root / relative_path
    if not absolute_path.exists() or not absolute_path.is_file():
        return []

    text = _decoded_file_text(absolute_path)

    errors: List[Dict[str, str]] = []
    for pattern_name, pattern in RISK_CONTROL_FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            errors.append(
                {
                    "kind": "risk_control_release_leak",
                    "file": relative_path,
                    "pattern": pattern_name,
                    "message": (
                        "Found internal versioning, private path, prediction artifact, "
                        "or row-level field in public risk-control release file."
                    ),
                }
            )
    return errors


def _check_metadata(repo_root: Path, warnings: List[str]) -> None:
    if not (repo_root / "LICENSE").exists():
        warnings.append("Missing root metadata file: LICENSE")
    if not (repo_root / "NOTICE").exists():
        warnings.append("Missing root metadata file: NOTICE")
    if not (repo_root / "requirements.txt").exists():
        warnings.append("Missing root metadata file: requirements.txt")
    if not (repo_root / "CONTRIBUTING.md").exists():
        warnings.append("Missing root metadata file: CONTRIBUTING.md")
    has_citation = (repo_root / "CITATION.cff").exists() or (repo_root / "CITATION.md").exists()
    if not has_citation:
        warnings.append("Missing root metadata file: CITATION.cff or CITATION.md")


def _check_risk_control_release(repo_root: Path, errors: List[Dict[str, str]]) -> None:
    tracked_files = _tracked_file_set(repo_root)
    for relative_path in RISK_CONTROL_RELEASE_REQUIRED_FILES:
        if not (repo_root / relative_path).exists():
            errors.append(
                {
                    "kind": "missing_risk_control_release_file",
                    "file": relative_path,
                    "pattern": "required_file",
                    "message": f"Missing required risk-control public release file: {relative_path}",
                }
            )
        elif relative_path not in tracked_files:
            errors.append(
                {
                    "kind": "untracked_risk_control_release_file",
                    "file": relative_path,
                    "pattern": "tracked_file",
                    "message": f"Required risk-control public release file is not tracked by git: {relative_path}",
                }
            )
        else:
            errors.extend(_scan_risk_control_release_file(repo_root, relative_path))

    performance_path = repo_root / "docs/public_release/performance_tables.json"
    if performance_path.exists():
        try:
            performance_payload = json.loads(performance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(
                {
                    "kind": "invalid_risk_control_json",
                    "file": "docs/public_release/performance_tables.json",
                    "pattern": "json",
                    "message": f"Invalid JSON: {exc}",
                }
            )
        else:
            serialized = json.dumps(performance_payload, sort_keys=True)
            if PUBLIC_MODEL_NAME not in serialized:
                errors.append(
                    {
                        "kind": "missing_public_model_name",
                        "file": "docs/public_release/performance_tables.json",
                        "pattern": PUBLIC_MODEL_NAME,
                        "message": "Performance table JSON does not identify the public model name.",
                    }
                )

    manifest_path = repo_root / "release/hove-risk-control-linker/manifest.json"
    if manifest_path.exists():
        try:
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(
                {
                    "kind": "invalid_risk_control_json",
                    "file": "release/hove-risk-control-linker/manifest.json",
                    "pattern": "json",
                    "message": f"Invalid JSON: {exc}",
                }
            )
        else:
            serialized = json.dumps(manifest_payload, sort_keys=True)
            if PUBLIC_MODEL_NAME not in serialized:
                errors.append(
                    {
                        "kind": "missing_public_model_name",
                        "file": "release/hove-risk-control-linker/manifest.json",
                        "pattern": PUBLIC_MODEL_NAME,
                        "message": "Checkpoint manifest does not identify the public model name.",
                    }
                )


def run_audit(
    repo_root: Path,
    allow_doc_local_paths: bool,
    require_risk_control_release: bool = False,
) -> Dict[str, object]:
    errors: List[Dict[str, str]] = []
    warnings: List[str] = []

    tracked_files: List[str] = []
    tracked_result = _run_git(["ls-files", "-z"], repo_root)
    if tracked_result.returncode != 0:
        errors.append(
            {
                "kind": "git_error",
                "file": "",
                "pattern": "git ls-files",
                "message": tracked_result.stderr.strip() or tracked_result.stdout.strip() or "Failed to list tracked files.",
            }
        )
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "checked_files": 0,
        }

    if tracked_result.stdout:
        tracked_files = [path for path in tracked_result.stdout.split("\0") if path]

    for relative_path in tracked_files:
        if _is_banned_path(relative_path):
            errors.append(
                {
                    "kind": "banned_root",
                    "file": relative_path,
                    "pattern": "banned_path",
                    "message": f"Tracked file is under a banned root: {relative_path}",
                }
            )
            continue

        errors.extend(_scan_file(repo_root, relative_path, allow_doc_local_paths))
        errors.extend(_scan_risk_control_release_file(repo_root, relative_path))

    _check_metadata(repo_root, warnings)
    if require_risk_control_release:
        _check_risk_control_release(repo_root, errors)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked_files": len(tracked_files),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run public-release audit checks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON result output.")
    parser.add_argument(
        "--allow-doc-local-paths",
        action="store_true",
        help=(
            "Allow documentation files to contain local absolute paths. "
            "Other file classes remain strict."
        ),
    )
    parser.add_argument(
        "--require-risk-control-release",
        action="store_true",
        help="Require and validate HOVE Risk-Control Linker public release artifacts.",
    )
    return parser.parse_args()


def _print_text_summary(result: Dict[str, object]) -> None:
    print(f"public-release audit: {'OK' if result['ok'] else 'FAIL'}")
    print(f"checked_files: {result['checked_files']}")

    for warning in result["warnings"]:
        print(f"warn: {warning}")

    for error in result["errors"]:
        print(
            f"error: {error['kind']} in {error['file']} ({error['pattern']}): {error['message']}"
        )


def main() -> int:
    args = _parse_args()
    try:
        repo_root = _repo_root(Path.cwd())
    except RuntimeError as exc:
        error_payload = {
            "ok": False,
            "errors": [
                {
                    "kind": "git_error",
                    "file": "",
                    "pattern": "git rev-parse",
                    "message": str(exc),
                }
            ],
            "warnings": [],
            "checked_files": 0,
        }
        if args.json:
            print(json.dumps(error_payload))
        else:
            _print_text_summary(error_payload)
        return 1

    result = run_audit(
        repo_root=repo_root,
        allow_doc_local_paths=args.allow_doc_local_paths,
        require_risk_control_release=args.require_risk_control_release,
    )
    if args.json:
        print(json.dumps(result))
    else:
        _print_text_summary(result)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
