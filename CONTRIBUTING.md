# Contributing

This repository is a public release package, not the private research
workspace. Contributions should preserve the public boundary:

- do not add clinical text, row-level predictions, generated datasets, or
  patient/note identifiers;
- do not add private artifact paths or internal experiment labels to public
  release files;
- keep concept-memory artifacts out of the repository unless redistribution is
  explicitly licensed;
- run the public audit and tests before opening a pull request.

Required checks:

```bash
python3 scripts/audit_public_release.py --allow-doc-local-paths --require-risk-control-release
python3 -m pytest tests/test_public_release_audit.py tests/test_hove_risk_control_release.py -q
```
