# HOVE Risk-Control Linker

## Model Card

- **Task**: Clinical concept linking risk-control and false-positive suppression.
- **Model family**: Re-ranking model with risk-aware calibration.
- **Scope**: Public release of aggregate metrics and reproducible packaging metadata.

## Intended Use

- Reduce severe-error / high-distance false positives.
- Compare with risk-aware references under equivalent candidate generation and evaluation setup.

## Claim Boundary

- This is a **severe-error/high-distance false-positive risk-control model**.
- This package does **not** claim clinical validation.
- This package does **not** claim production deployment readiness.
- This package does **not** claim state-of-the-art status.
- Concept memory bundle is regeneration-required unless redistribution is permitted by the controlling ontology license.

## Public Outputs

- `performance_tables.md`
- `performance_tables.json`
- `release/hove-risk-control-linker/manifest.json`
- Public figures when source assets are available.

## Non-goals in this public pack

- No row-level prediction dumps.
- No restricted training data or local absolute paths.
- No internal version tags in public text.

## Citation

If you use this public material, cite the original corresponding publication and follow the data usage terms of the underlying resources.

## License and Source Terms

- Repository code, documentation, tests, release scripts, and public aggregate metadata: MIT License, https://opensource.org/license/mit.
- Packaged checkpoint and config: public research artifacts in this repository; no row-level predictions, training rows, clinical text, patient/document identifiers, mention offsets, or concept-memory bundle are included.
- MIMIC-IV-Note: https://physionet.org/content/mimic-iv-note/
- PhysioNet credentialed access and data-use terms: https://physionet.org/content/mimiciv/view-dua/1.0/
- OMOP Common Data Model: https://www.ohdsi.org/data-standardization/the-common-data-model/
- OHDSI Athena vocabulary access: https://athena.ohdsi.org/
- MedCAT: https://github.com/CogStack/MedCAT

## Contact

Please route requests through the repository’s issue tracker or release notes for the public project.
