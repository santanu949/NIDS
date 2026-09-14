# Data Preprocessing – Phase 2

## Dataset

**UNSW-NB15** – University of New South Wales Network Benchmark 2015.
A publicly available network intrusion dataset containing both benign and
attack traffic across 9 attack categories.

---

## File Locations

| Purpose | Path |
|---|---|
| Raw training CSV | `backend/data/raw/UNSW_NB15_training-set.csv` |
| Raw testing CSV  | `backend/data/raw/UNSW_NB15_testing-set.csv` |
| Feature schema   | `backend/data/feature_schema.json` |
| Audit JSON       | `backend/data/audit_report.json` |
| Audit TXT        | `backend/data/audit_report.txt` |
| Fitted pipeline  | `backend/ml/artifacts/preprocessor.joblib` |
| Validation indices | `backend/ml/artifacts/val_indices.json` |

---

## Train / Test Sizes

| Split | Rows | Columns |
|---|---|---|
| Training | 175,341 | 45 |
| Testing  |  82,332 | 45 |

> **Important**: The official UNSW-NB15 CSV split is **preserved intact**.
> Training and testing CSVs are never randomly merged.

---

## 45-Column Schema

```
id, dur, proto, service, state, spkts, dpkts, sbytes, dbytes, rate,
sttl, dttl, sload, dload, sloss, dloss, sinpkt, dinpkt, sjit, djit,
swin, stcpb, dtcpb, dwin, tcprtt, synack, ackdat, smean, dmean,
trans_depth, response_body_len, ct_srv_src, ct_state_ttl, ct_dst_ltm,
ct_src_dport_ltm, ct_dst_sport_ltm, ct_dst_src_ltm, is_ftp_login,
ct_ftp_cmd, ct_flw_http_mthd, ct_src_ltm, ct_srv_dst,
is_sm_ips_ports, attack_cat, label
```

---

## Binary Target Definition

| Column | Role |
|---|---|
| `label` | **Binary target** – `0` = Normal, `1` = Attack |

Label distribution:

| Split | Normal (0) | Attack (1) |
|---|---|---|
| Train |  56,000 | 119,341 |
| Test  |  37,000 |  45,332 |

---

## `attack_cat` Handling

`attack_cat` is a **multi-class analysis field**, not a model feature.

- It is excluded from the feature matrix `X` for this phase.
- It is retained in the raw CSVs and the `feature_schema.json` for future
  multiclass detection work.
- **Never** encode `attack_cat` as an input feature.

| Category | Training count | Testing count |
|---|---|---|
| Normal | 56,000 | 37,000 |
| Generic | 40,000 | 18,871 |
| Exploits | 33,393 | 11,132 |
| Fuzzers | 18,184 | 6,062 |
| DoS | 12,264 | 4,089 |
| Reconnaissance | 10,491 | 3,496 |
| Analysis | 2,000 | 677 |
| Backdoor | 1,746 | 583 |
| Shellcode | 1,133 | 378 |
| Worms | 130 | 44 |

---

## Excluded Columns and Reasons

| Column | Reason |
|---|---|
| `id` | Non-predictive sequential row identifier. Contains no network semantics. Including it would leak row ordering and cause overfitting to dataset artifacts. |
| `label` | Binary target variable. Must never appear in `X`. |
| `attack_cat` | Multi-class target / analysis field. Reserved for future multiclass detection. |

---

## Numeric Feature Columns (39)

```
dur, spkts, dpkts, sbytes, dbytes, rate,
sttl, dttl, sload, dload, sloss, dloss,
sinpkt, dinpkt, sjit, djit,
swin, stcpb, dtcpb, dwin,
tcprtt, synack, ackdat, smean, dmean,
trans_depth, response_body_len,
ct_srv_src, ct_state_ttl, ct_dst_ltm,
ct_src_dport_ltm, ct_dst_sport_ltm, ct_dst_src_ltm,
is_ftp_login, ct_ftp_cmd, ct_flw_http_mthd,
ct_src_ltm, ct_srv_dst, is_sm_ips_ports
```

---

## Categorical Feature Columns (3)

| Column | Description |
|---|---|
| `proto` | Network protocol (e.g., tcp, udp, icmp) |
| `service` | Application service (e.g., http, ftp, dns) |
| `state` | Connection state (e.g., FIN, INT, CON) |

---

## Missing / Infinite Value Handling

### Missing Values
- **Audit finding**: 0 missing values in both training and testing CSVs.
- **Pipeline strategy**: `SimpleImputer(strategy="median")` for numeric;
  `SimpleImputer(strategy="most_frequent")` for categorical.
- **Rationale**: Inference data may contain missing values. The pipeline
  must handle them gracefully.

### Infinite Values
- **Audit finding**: checked programmatically (see `audit_report.json`).
- **Strategy**: `np.inf` and `-np.inf` are replaced with `np.nan` via
  `replace_infinities()` **before** the sklearn pipeline runs.
- This converts infinities into missing values that the imputer then handles.
- This step is applied identically to training and inference data.

---

## Categorical Encoding

`OneHotEncoder(handle_unknown="ignore", sparse_output=False)`

- **Fitted on training data only**.
- At inference, unseen categories produce all-zero rows (no error raised).
- Dense output for compatibility with downstream estimators.

---

## Scaling Decision

`StandardScaler()` applied to **numeric features only**, inside the pipeline.

| Consideration | Decision |
|---|---|
| Required for distance-based models (SVM, k-NN, logistic regression) | ✅ Include |
| Tree-based models (Random Forest, XGBoost) mathematically unaffected | No harm – scaling inside pipeline is transparent |
| Applied inside Pipeline → consistent at inference | ✅ Safe |
| Fitted on training partition only | ✅ No leakage |

---

## Leakage Prevention

1. **Fit only on training data**: All transformers (`SimpleImputer`,
   `StandardScaler`, `OneHotEncoder`) are fitted exclusively on the
   training partition of the official training CSV.
2. **Test set untouched**: The test CSV is never passed to `.fit()`.
3. **`remainder="drop"`**: The `ColumnTransformer` silently drops any
   columns not in `numeric_feature_columns` or `categorical_feature_columns`.
   This prevents stray columns from leaking into the feature matrix.
4. **`prepare_Xy()`** explicitly asserts that `label`, `attack_cat`, and
   `id` are absent from `X`.
5. **Validation split is internal**: The 20% validation split is created
   from the training CSV only. The test CSV is reserved for final evaluation.

---

## Train / Validation / Test Strategy

```
Official UNSW-NB15 training CSV (175,341 rows)
    ├── Training partition:   ~140,272 rows  (80%, stratified)
    └── Validation partition: ~35,069  rows  (20%, stratified)

Official UNSW-NB15 testing CSV (82,332 rows)
    └── Final evaluation only (never seen during preprocessing fit)
```

- Stratified split by `label` with `random_state=42`.
- Validation indices saved to `backend/ml/artifacts/val_indices.json`.

---

## Artifact Locations

| Artifact | Path | Purpose |
|---|---|---|
| Feature schema | `backend/data/feature_schema.json` | Column lists, exclusions, target |
| Audit JSON | `backend/data/audit_report.json` | Machine-readable audit findings |
| Audit TXT | `backend/data/audit_report.txt` | Human-readable audit findings |
| Fitted preprocessor | `backend/ml/artifacts/preprocessor.joblib` | Reuse at training and inference |
| Validation indices | `backend/ml/artifacts/val_indices.json` | Reproducible train/val split |

---

## How to Run the Audit

```bash
# From the project root (nids-ml/)
python -m backend.ml.audit
# -- or --
python backend/ml/audit.py
```

Outputs:
- `backend/data/audit_report.json`
- `backend/data/audit_report.txt`

---

## How to Run Preprocessing

```bash
# From the project root (nids-ml/)
python -m backend.ml.preprocess
# -- or --
python backend/ml/preprocess.py
```

This fits and saves `backend/ml/artifacts/preprocessor.joblib`.

## How to Run Validation Checks

```bash
# From the project root (nids-ml/)
python -m backend.ml.validate
# -- or --
python backend/ml/validate.py
```

Runs 12 checks and exits with code 0 on success, 1 on failure.

---

## Known Limitations

1. **No model trained yet.** No accuracy, precision, recall, or F1 scores
   are available. Phase 2 is preprocessing only.
2. **`is_ftp_login`, `ct_ftp_cmd`, `ct_flw_http_mthd`** are treated as
   numeric. The audit will reveal whether they behave as sparse/near-zero
   columns. Inclusion is justified until a trained model's feature importance
   indicates otherwise.
3. **Class imbalance** is documented but not addressed in this phase.
   Techniques (SMOTE, class weights, threshold tuning) belong in the model
   training phase.
4. **Feature importance / selection** has not been applied. All 42 features
   are passed to the pipeline. A trained model's coefficients or SHAP values
   should guide future pruning.
5. **StandardScaler** inside the pipeline adds overhead for tree-based models
   but causes no correctness issue. The decision to include/exclude it can be
   revisited at training time without rewriting the pipeline structure.
