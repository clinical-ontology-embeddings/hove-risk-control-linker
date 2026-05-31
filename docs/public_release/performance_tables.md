# HOVE Risk-Control Linker Performance

## Main Evaluation Rows

| Model | F1 | Exact | Link Acc | Severity per Gold | HDFP per Row |
|---|---|---|---|---|---|
| unfiltered top3 | 0.4310 | 0.4840 | 0.9007 | 7.3207 | 1.9527 |
| similarity >=0.85 | 0.5572 | 0.4721 | 0.9123 | 4.3149 | 0.7326 |
| base scalar reference | 0.5720 | 0.4651 | 0.9089 | 4.0368 | 0.6117 |
| risk-aware scalar reference | 0.5760 | 0.4571 | 0.9113 | 3.8948 | 0.5375 |
| HOVE Risk-Control Linker | 0.6660 | 0.4794 | 0.9119 | 2.8358 | 0.1610 |

## Bootstrap Deltas

| Variant | F1 Δ | Exact Δ | Link Acc Δ | Severity Δ | HDFP Δ | F1 CI | Exact CI | Link Acc CI | Severity CI | HDFP CI |
|---|---|---|---|---|---|---|---|---|---|---|
| linker_vs_risk_scalar | 0.0899 | 0.0223 | 0.0006 | -1.0590 | -0.3765 | [0.0891, 0.0906] | [0.0217, 0.0228] | [0.0001, 0.0012] | [-1.0662, -1.0501] | [-0.3786, -0.3740] |
| linker_vs_base_scalar | 0.0940 | 0.0143 | 0.0030 | -1.2010 | -0.4507 | [0.0934, 0.0946] | [0.0138, 0.0147] | [0.0025, 0.0035] | [-1.2085, -1.1921] | [-0.4533, -0.4482] |

## Ablation Rows

| Variant | Threshold | Positive Rate | F1 | Exact | Link Acc | Severity per Gold | HDFP per Row |
|---|---|---|---|---|---|---|---|
| final true risk-aware near123 | 0.4500 | 0.3487 | 0.6660 | 0.4794 | 0.9119 | 2.8358 | 0.1610 |
| matched true risk-aware near123 | 0.1000 | 0.3493 | 0.6449 | 0.4691 | 0.9137 | 3.0236 | 0.2121 |
| exact-only | 0.0500 | 0.3184 | 0.6091 | 0.4706 | 0.9944 | 3.1339 | 0.2155 |
| randomized risk-aware near123 | 0.0500 | 0.3521 | 0.6458 | 0.4710 | 0.9065 | 3.0639 | 0.2439 |
| degree-depth-random risk-aware near123 | 0.0500 | 0.3498 | 0.6426 | 0.4708 | 0.9140 | 3.0670 | 0.2411 |
| with ontology node features | 0.0500 | -- | 0.6436 | 0.4713 | 0.9133 | 3.0537 | 0.2289 |

## Scope

- Severe-error/high-distance false-positive risk control focus.
- No deployment-ready claim is made.
- This release does not contain row-level predictions.
- Concept-memory bundle is not redistributed in this public package.
