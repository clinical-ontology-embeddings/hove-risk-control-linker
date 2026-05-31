import json
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_public_release.py"


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)


def _run_audit(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result


def _add_tracked_file(repo_path: Path, path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    subprocess.run(["git", "add", str(path.relative_to(repo_path))], cwd=repo_path, check=True, capture_output=True, text=True)


def _api_key_pattern() -> str:
    return "api_" + "key="


def _secret_key_pattern() -> str:
    return "secret" + "-key"


def test_banned_tracked_root_fails(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "data" / "private.csv", "a,b\n1,2\n")
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert any("data" in error["file"] and error["kind"] == "banned_root" for error in payload["errors"])


def test_third_party_clone_root_fails(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "third_party" / "other_clone" / "README.md", "vendored clone")
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(
        error["file"] == "third_party/other_clone/README.md" and error["kind"] == "banned_root"
        for error in payload["errors"]
    )


def test_env_variant_file_fails(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / ".env.local", "LOCAL_ONLY=yes\n")
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(error["file"] == ".env.local" and error["kind"] == "banned_root" for error in payload["errors"])


def test_forbidden_patterns_fail_even_with_allow_doc_flag(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "src" / "config.py", f"{_api_key_pattern()}abc123\n")
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--allow-doc-local-paths", "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert any(
        error["kind"] == "forbidden_pattern" and error["pattern"] == _api_key_pattern()
        for error in payload["errors"]
    )


def _build_home_user_path() -> str:
    return "/".join(["", "home", "user", ""])


def test_docs_home_user_path_allowed_only_with_flag(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(
        repo,
        repo / "docs" / "history.md",
        f"Historical path: {_build_home_user_path()}somewhere",
    )
    _add_tracked_file(repo, repo / "README.md", "ok")

    strict_result = _run_audit(repo, "--json")
    assert strict_result.returncode == 1
    strict_payload = json.loads(strict_result.stdout)
    assert any(_build_home_user_path() in error["pattern"] for error in strict_payload["errors"])

    allowed_result = _run_audit(repo, "--json", "--allow-doc-local-paths")
    assert allowed_result.returncode == 0
    allowed_payload = json.loads(allowed_result.stdout)
    assert allowed_payload["ok"]
    assert not allowed_payload["errors"]


def test_missing_metadata_files_create_warnings(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"]
    assert any("LICENSE" in warning for warning in payload["warnings"])
    assert any("NOTICE" in warning for warning in payload["warnings"])
    assert any("requirements.txt" in warning for warning in payload["warnings"])
    assert any("CONTRIBUTING.md" in warning for warning in payload["warnings"])
    assert any("CITATION" in warning for warning in payload["warnings"])


def test_gitignore_secret_guard_pattern_is_allowed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / ".gitignore", f"{_secret_key_pattern()}-*\\n")
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"]


def test_json_output_format_is_machine_readable(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)

    assert set(payload.keys()) == {"ok", "errors", "warnings", "checked_files"}
    assert isinstance(payload["ok"], bool)
    assert isinstance(payload["errors"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["checked_files"], int)


def _add_minimal_risk_control_release(repo_path: Path) -> None:
    release_files = {
        "scripts/make_hove_risk_control_release.py": (
            'PUBLIC_MODEL_NAME = "HOVE Risk-Control Linker"\n'
        ),
        "NOTICE": "# Notice\n",
        "requirements.txt": "pytest==9.0.3\n",
        "docs/public_release/model_card.md": "# HOVE Risk-Control Linker\n",
        "docs/public_release/performance_tables.md": "# HOVE Risk-Control Linker\n",
        "docs/public_release/performance_tables.json": json.dumps(
            {"model_name": "HOVE Risk-Control Linker"}
        ),
        "docs/public_release/figures/hove_risk_control_linker_overview.png": "png\n",
        "docs/public_release/figures/hove_risk_control_linker_overview.pdf": "%PDF-1.4\n",
        "docs/public_release/figures/risk_control_pipeline.png": "png\n",
        "docs/public_release/figures/risk_control_pipeline.pdf": "%PDF-1.4\n",
        "docs/public_release/figures/risk_frontier.png": "png\n",
        "docs/public_release/figures/risk_frontier.pdf": "%PDF-1.4\n",
        "release/hove-risk-control-linker/manifest.json": json.dumps(
            {"model_name": "HOVE Risk-Control Linker", "artifacts": []}
        ),
        "release/hove-risk-control-linker/risk_control_linker_config.json": json.dumps(
            {"public_model_name": "HOVE Risk-Control Linker", "decision_threshold": 0.45}
        ),
        "release/hove-risk-control-linker/risk_control_linker.pt": "checkpoint\n",
        "README.md": "ok",
    }
    for relative_path, content in release_files.items():
        _add_tracked_file(repo_path, repo_path / relative_path, content)


def test_required_risk_control_release_flag_fails_when_artifacts_are_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_tracked_file(repo, repo / "README.md", "ok")

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(
        error["kind"] == "missing_risk_control_release_file"
        and error["file"] == "docs/public_release/model_card.md"
        for error in payload["errors"]
    )


def test_required_risk_control_release_flag_accepts_sanitized_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_minimal_risk_control_release(repo)

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"]


def test_required_risk_control_release_flag_rejects_untracked_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_minimal_risk_control_release(repo)
    untracked = repo / "docs" / "public_release" / "model_card.md"
    subprocess.run(
        ["git", "rm", "--cached", str(untracked.relative_to(repo))],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(
        error["kind"] == "untracked_risk_control_release_file"
        and error["file"] == "docs/public_release/model_card.md"
        for error in payload["errors"]
    )


def test_risk_control_release_files_reject_internal_versions_and_row_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_minimal_risk_control_release(repo)
    leaked_text = "Internal " + "V" + "502" + " path test_filtered_predictions.jsonl note_id"
    _add_tracked_file(repo, repo / "docs" / "public_release" / "model_card.md", leaked_text)

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    leak_errors = [
        error for error in payload["errors"] if error["kind"] == "risk_control_release_leak"
    ]
    assert {error["pattern"] for error in leak_errors} >= {
        "internal_version",
        "prediction_jsonl",
        "row_note_id",
    }


def test_risk_control_release_scans_root_readme(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_minimal_risk_control_release(repo)
    _add_tracked_file(repo, repo / "README.md", "Public page with internal " + "V" + "502")

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(
        error["kind"] == "risk_control_release_leak"
        and error["file"] == "README.md"
        and error["pattern"] == "internal_version"
        for error in payload["errors"]
    )


def test_risk_control_release_scans_binary_payload_strings(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    _add_minimal_risk_control_release(repo)
    checkpoint = repo / "release" / "hove-risk-control-linker" / "risk_control_linker.pt"
    checkpoint.write_bytes(b"\x00\x01safe header\nV" + b"502" + b"\x00")
    subprocess.run(["git", "add", str(checkpoint.relative_to(repo))], cwd=repo, check=True, capture_output=True, text=True)

    proc = _run_audit(repo, "--json", "--require-risk-control-release")

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert any(
        error["kind"] == "risk_control_release_leak"
        and error["file"] == "release/hove-risk-control-linker/risk_control_linker.pt"
        and error["pattern"] == "internal_version"
        for error in payload["errors"]
    )
