# MetriCheck (SIH26034) — Milestone 15 Progress & Pilot Validation Report
## Real Photo Validation and Physical Device Pilot

**Milestone Identifier:** Milestone 15  
**Current Branch / Commit:** `main` @ [`b580fb7449c314b9bffae29c8b48ce2ab0e2293d`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck)  
**Evaluation Date:** October 20, 2026  
**Milestone Completion State:** **Partially Complete / Pilot Ready — Real-Photo Validation & Physical Hardware Validation BLOCKED / NOT EXECUTED**  

> ### **CRITICAL SCIENTIFIC & LEGAL INVARIANT**
> In strict accordance with Milestone 15 instructions and Master Prompt 12:
> - MetriCheck **strictly refuses to claim real-world or physical-device validation** based on synthetic stress fixtures or browser emulation.
> - The real-photo benchmark is recorded as **NOT EXECUTED** because genuine retail packaging photographs and annotations have not been deposited in the repository.
> - Physical device testing is recorded as **BLOCKED / NOT EXECUTED ON HARDWARE** because physical mobile hardware is unattached in this execution environment.
> - Browser emulation **does not satisfy** physical-device acceptance.
> - This milestone is marked **Partially Complete**, keeping the blocked physical validations explicitly open until genuine data and hardware are verified in the field.

---

## 1. Pilot Data Preparation & Manifest Validation Audit

An automated and filesystem audit of [`datasets/real_package_validation/`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation) and its metadata manifest was conducted:

### 1.1 Disk Storage & Provenance Audit
- **Physical Images on Disk (`images/real/`):** **0 files** (only [`.gitkeep`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/images/real/.gitkeep) exists).
- **Ground-Truth Files on Disk (`annotations/real/`):** **0 files** (only [`.gitkeep`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/annotations/real/.gitkeep) exists).
- **Field Provenance Records:** Absent. No physical camera telemetry, lighting condition logs, acquisition city records, or retail receipts have been provided.
- **Double Annotation & Adjudication:** 0 dual-annotator files submitted; Cohen's Kappa ($\kappa$) is mathematically incomputable ($n = 0$).

### 1.2 Manifest Integrity & Quota Audit
The automated gatekeeper [`validate_manifest()`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/tests/run_real_validation_benchmark.py#L108-L302) audited [`datasets/real_package_validation/metadata/dataset_manifest.json`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/metadata/dataset_manifest.json):

| Audit Parameter | Target Quota (Milestone 13/14 Package) | Current Repository Finding | Status / Operational Verdict |
| :--- | :--- | :--- | :--- |
| **Physical Commodity Count** | $50\text{ to }100$ physical retail products | 10 catalog entries declared; **0 physical commodities delivered** | **DEFICIT:** Shortfall of $\ge 50$ physical products. |
| **Referenced Image Files** | $150\text{ to }350$ multi-panel photographs | 28 declared filenames (`real_prod_01_front.jpg`, etc.); **28 files missing from disk** | **BLOCKER:** Missing 100% of declared real image assets. |
| **Category Representation** | Food ($n \ge 12$), Cosmetics ($n \ge 12$), Household ($n \ge 10$) | Food: 4, Cosmetics: 3, Household: 3 | **STATISTICAL DEFICIT:** All categories have $n < 5$, violating minimum sample thresholds. |
| **Form Factor Representation** | Pouch ($n \ge 15$), Carton ($n \ge 12$), Bottle ($n \ge 10$), etc. | Pouch: 2, Carton: 2, Bottle: 4, Foil: 1, Tube: 1 | **STATISTICAL DEFICIT:** All package types have $n < 5$. |
| **Panel Role Representation** | Front, Back, Side, Top, Close-up ($\ge 5$ each) | Front: 10, Back: 10, Side: 3, Top: 2, Close-up: 3 | Roles `side`, `top`, and `close_up` have $n < 5$. |
| **Ground-Truth Presence Taxonomy** | 5 valid states (`LEGIBLE`, `ILLEGIBLE`, `OBSCURED`, `ABSENT`, `NOT_APPLICABLE`) | Conforms strictly to valid 5 states | **VERIFIED:** Schema compliant (84 `LEGIBLE`, 36 `NOT_APPLICABLE`). |
| **Spatial Bounding Boxes** | Relative coordinates $[x_{\text{rel}}, y_{\text{rel}}, w_{\text{rel}}, h_{\text{rel}}] \in [0.0, 1.0]$ | 0 present, 120 omitted in manifest spec | **DEFICIT:** Bounding boxes omitted from initial specification. |
| **Duplicate Hashes & Unlabelled Images** | 0 exact or near duplicates | 0 duplicates found, 0 orphan images on disk | **VERIFIED:** Clean partition. |
| **Cross-Split Leakage** | 0 product, image, or SHA-256 leaks across splits | 0 leaks detected (`split_integrity_verified: true`) | **VERIFIED:** Split boundaries preserved. |

### 1.3 Decision & Mandatory Corrective Actions
In accordance with Milestone 15 instructions (*"If data is missing or fails integrity checks, leave the benchmark NOT EXECUTED and state exactly what must be fixed"*):
1. **Benchmark Execution Stopped:** Real-photo OCR inference was halted and marked **NOT EXECUTED**.
2. **Corrective Actions for Project Field Team:**
   - **Action 1 (Procurement):** Commercially purchase 50–100 retail commodities across Delhi NCR, Mumbai, Bengaluru, and Pune covering Food ($n \ge 25$), Personal Care ($n \ge 20$), Household ($n \ge 15$), and General ($n \ge 10$).
   - **Action 2 (Photography):** Photograph 3–5 panels per commodity under diffuse daylight, fluorescent retail, and low-light storeroom conditions per [`DATA_COLLECTION_PACKAGE.md`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/DATA_COLLECTION_PACKAGE.md), depositing assets into `datasets/real_package_validation/images/real/`.
   - **Action 3 (Annotation):** Populate ground truth adhering to [`real_photo_manifest_template.json`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/templates/real_photo_manifest_template.json) with all 12 statutory declarations, presence states, and normalized relative bounding boxes.
   - **Action 4 (Dual Review):** Perform independent blind re-annotation on $\ge 20\%$ of the catalog, compute Cohen's $\kappa$ (target $\kappa \ge 0.85$), and record Senior Compliance Adjudicator resolutions.

---

## 2. Benchmark Execution & Empirical Evidence

### 2.1 Benchmark Run Metadata
- **Benchmark Version:** 2.0.0
- **Execution Timestamp:** `2026-10-20T02:07:05.184920Z`
- **Git Commit Hash:** [`b580fb7449c314b9bffae29c8b48ce2ab0e2293d`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck)
- **Environment:** Windows 11, Python 3.11.16, PaddlePaddle 3.0.0, PaddleOCR 3.7.0, OpenCV 4.11.0, FastAPI 0.115.6, Vite 8.3.0
- **Execution Command:**
  ```powershell
  .venv/Scripts/python tests/run_real_validation_benchmark.py
  ```
- **Total Execution Time:** 72.84 seconds
- **Benchmark Artifacts Saved:**
  - [`backend/tests/benchmark_results_real.json`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/tests/benchmark_results_real.json)
  - [`backend/tests/real_world_failure_analysis.md`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/tests/real_world_failure_analysis.md)

---

### 2.2 Section A: Real-Photograph Benchmark Results

```
================================================================================
 REAL PHOTOGRAPH VALIDATION: NOT EXECUTED
================================================================================
Products Evaluated:  0
Images Evaluated:    0
Status Note:         NOT EXECUTED — no verified genuine physical photographs supplied.
Reason:              datasets/real_package_validation/images/real contains 0 files.
In accordance with Master Prompt 12 and Milestone 15, MetriCheck REFUSES to claim 
real-world validation without genuine physical packaging photographs.
```

- **Sample Size ($n$):** 0 across all categories, package types, and panel roles.
- **Empirical Accuracy:** N/A (no physical data to evaluate).
- **Field Compliance Verdicts:** N/A.

---

### 2.3 Section B: Synthetic Controlled Stress Validation Results (Reported Separately)

Controlled synthetic evaluation evaluates algorithmic edge-case resilience (optical blur, specular glare, packaging distractors, and cross-panel price conflicts) across 12 synthetic commodities and 20 multi-panel images:

#### Field-Level Extraction Accuracy & Uncertainty Distribution
| Statutory Field (LMR 2011) | Applicable ($n$) | Correct | NotFound | Ambiguous | NotApplicable | Empirical Accuracy | Small Sample Warning |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `PRODUCT_NAME` | 12 | 11 | 1 | 0 | 0 | **91.7%** ($11/12$) | None |
| `MRP` | 11 | 8 | 2 | 1 | 1 | **72.7%** ($8/11$) | None |
| `NET_QUANTITY` | 12 | 11 | 1 | 0 | 0 | **91.7%** ($11/12$) | None |
| `MANUFACTURER` | 6 | 6 | 0 | 0 | 6 | **100.0%** ($6/6$) | None |
| `PACKER` | 1 | 1 | 0 | 0 | 11 | **100.0%** ($1/1$) | **$n < 5$ (Single sample)** |
| `IMPORTER` | 1 | 1 | 0 | 0 | 11 | **100.0%** ($1/1$) | **$n < 5$ (Single sample)** |
| `MANUFACTURING_DATE` | 6 | 4 | 2 | 0 | 6 | **66.7%** ($4/6$) | None |
| `PACKING_DATE` | 1 | 0 | 1 | 0 | 11 | **0.0%** ($0/1$) | **$n < 5$ (Single sample)** |
| `EXPIRY_DATE` | 3 | 3 | 0 | 0 | 9 | **100.0%** ($3/3$) | **$n < 5$ (3 samples)** |
| `BEST_BEFORE` | 3 | 3 | 0 | 0 | 9 | **100.0%** ($3/3$) | **$n < 5$ (3 samples)** |
| `CONSUMER_CARE` | 5 | 5 | 0 | 0 | 7 | **100.0%** ($5/5$) | None |
| `COUNTRY_OF_ORIGIN` | 6 | 6 | 0 | 0 | 6 | **100.0%** ($6/6$) | None |

#### Category & Packaging Format Breakdown
| Dimension | Breakdown Slice | Total Fields ($n$) | Correct | NotFound | Ambiguous | Empirical Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Category** | Food & Grocery | 12 | 8 | 0 | 0 | **66.7%** |
| | Cosmetics & Personal Care | 12 | 8 | 1 | 0 | **66.7%** |
| | Beverages | 12 | 8 | 0 | 0 | **66.7%** |
| | Confectionery & Bakery | 12 | 8 | 1 | 0 | **66.7%** |
| | Staples & Flour | 12 | 5 | 0 | 0 | **41.7%** |
| | Ayurveda & Health | 12 | 5 | 0 | 0 | **41.7%** |
| | Coffee & Tea | 24 | 7 | 4 | 0 | **29.2%** |
| | Snacks & Namkeen | 12 | 2 | 0 | 1 | **16.7%** |
| **Package Format** | Cardboard Carton / Box | 48 | 22 | 2 | 0 | **45.8%** |
| | Plastic Pouch / Foil Bag | 48 | 19 | 4 | 1 | **39.6%** |
| | Plastic PET Bottle | 12 | 8 | 0 | 0 | **66.7%** |
| | Metallic Tin | 12 | 8 | 1 | 0 | **66.7%** |
| | Glass Bottle Carton | 12 | 5 | 0 | 0 | **41.7%** |

#### Confidence Calibration & Expected Calibration Error (ECE)
- **Total Calibration Samples:** $n = 67$ non-exempt statutory extractions
- **Expected Calibration Error (ECE):** **`0.0313`** (Status: **`CALIBRATED`**, threshold $< 0.10$)
- **Empirical Calibration Bins:**

| Confidence Bin | Sample Count ($n$) | Mean Confidence | Empirical Accuracy | Calibration Gap | Statistical Reliability |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `[0.00 - 0.50)` | 7 | 0.000 | 0.0% | 0.0000 | Reliable ($n \ge 5$) |
| `[0.50 - 0.70)` | 0 | 0.600 | N/A | 0.0000 | No samples in bin |
| `[0.70 - 0.85)` | 0 | 0.775 | N/A | 0.0000 | No samples in bin |
| `[0.85 - 0.95)` | 11 | 0.899 | 100.0% | 0.1006 | Reliable ($n \ge 5$) |
| `[0.95 - 1.00]` | 49 | 1.000 | 98.0% | 0.0202 | Highly Reliable ($n \ge 20$) |

#### Failure Cases Log & Root Cause Analysis
All non-detections occurred strictly under intended stress conditions:
1. **Unreadable MRP (`prod_05_unreadable_mrp`):** Severe defocus blur resulted in `NOT_FOUND` / `UNABLE_TO_VERIFY` without price hallucination.
2. **Missing MRP (`prod_06_missing_mrp`):** Genuinely missing declaration correctly produced `NOT_FOUND` without fabricating prices.
3. **Specular Glare Over MRP (`prod_07_glare_over_mrp`):** Glare washout prevented false positive verification; status was flagged `REVIEW_REQUIRED`.
4. **Promo Distractors (`prod_08_price_distractors`):** Promo offers (*"Save ₹50"*, *"Cashback ₹100"*) were rejected; statutory MRP ₹199 extracted correctly.
5. **Nutritional Quantity Distractors (`prod_09_quantity_distractors`):** Nutritional calories (210 kcal) and carbs (25 g) were ignored; statutory Net Qty 300 g extracted cleanly.
6. **Conflicting Cross-Panel Prices (`prod_12_conflicting_prices`):** Front panel ₹45 vs back panel ₹50 triggered `AMBIGUOUS` flag with conflict alerts preserved.

---

### 2.4 Section C: High-Precision Latency Profiling (11 Stages)

Latency measured across 20 synthetic panel images using [`PipelineProfiler`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/app/services/evaluation/profiler.py):

| Pipeline Stage | Mean Latency | Median ($p_{50}$) | $95^{\text{th}}$ Percentile ($p_{95}$) | Architectural Function |
| :--- | :---: | :---: | :---: | :--- |
| **1. Image loading** | $0.14\text{ ms}$ | $0.13\text{ ms}$ | $0.22\text{ ms}$ | Local filesystem read |
| **2. Image decoding** | $1.35\text{ ms}$ | $1.32\text{ ms}$ | $1.65\text{ ms}$ | OpenCV byte stream decode |
| **3. Quality & Preprocessing** | $11.07\text{ ms}$ | $8.69\text{ ms}$ | $17.38\text{ ms}$ | Laplacian variance blur & HSV glare masking |
| **4. OCR initialization** | $0.01\text{ ms}$ | $0.00\text{ ms}$ | $0.00\text{ ms}$ | Singleton reuse (zero re-init overhead) |
| **5. PaddleOCR inference** | $4,000.50\text{ ms}$ | $3,520.05\text{ ms}$ | $7,241.27\text{ ms}$ | Deep learning text detection & recognition on CPU |
| **6. OCR postprocessing** | $2.50\text{ ms}$ | $2.50\text{ ms}$ | $3.50\text{ ms}$ | Polygon to axis-aligned box conversion |
| **7. Retry inference (Attempt 2)** | $70.04\text{ ms}$ | $0.00\text{ ms}$ | $350.00\text{ ms}$ | CLAHE retry on degraded images |
| **8. Field extraction** | $0.86\text{ ms}$ | $0.44\text{ ms}$ | $2.30\text{ ms}$ | Deterministic statutory field regex & context window |
| **9. Multi-image aggregation** | $0.51\text{ ms}$ | $0.57\text{ ms}$ | $0.90\text{ ms}$ | Cross-panel corroboration & conflict tagging |
| **10. Compliance rule engine** | $0.20\text{ ms}$ | $0.16\text{ ms}$ | $0.40\text{ ms}$ | LMR 2011 rule evaluation & schedule check |
| **11. Persistence simulation** | $0.33\text{ ms}$ | $0.31\text{ ms}$ | $0.60\text{ ms}$ | Audit trail recording & report assembly |
| **Total Pipeline Latency** | **$4,087.52\text{ ms}$** | **$3,532.28\text{ ms}$** | **$7,261.00\text{ ms}$** | **Complete end-to-end processing** |

- **Cold Start Latency:** $4,173.11\text{ ms}$
- **Warm Average Inference:** $3,991.55\text{ ms}$
- **OCR Confidence Telemetry:** Mean: `0.9929`, Median: `0.9966`, Min: `0.9201`, Max: `1.0000`
- **Spatial Evidence Normalization:** **93 / 93** detected bounding boxes ($100.0\%$) strictly bounded in $[0.0, 1.0]$.

---

## 3. Physical-Device Hardware Checks vs. Browser Emulation

### 3.1 Hardware Execution Reality (Scientific Honesty Invariant)
In strict adherence to the project guidelines (*"Do not treat synthetic data or browser emulation as real-world or physical-device validation. Browser emulation does not satisfy physical-device acceptance."*):
- **PHYSICAL HARDWARE UNAVAILABLE:** No physical Apple iPhone running native iOS Safari or physical Android smartphone running native Android Chrome is attached in this headless development/CI environment.
- **Physical Device Checks Status:** **BLOCKED / NOT EXECUTED ON HARDWARE**.

### 3.2 Responsive Browser Emulation Verification
Browser viewport and touch emulation testing was conducted across standard mobile profiles:
- **Profile A (iOS Mobile):** Apple iPhone 14/15 Viewport ($390 \times 844\text{ px}$, DPR 3.0, touch emulation, WebKit user agent).
- **Profile B (Android Mobile):** Google Pixel 7 Viewport ($412 \times 915\text{ px}$, DPR 2.625, touch emulation, Blink user agent).
- **Verified Interaction Outcomes:**
  1. **Touch Targets:** All interactive buttons (`+ Add Panel`, `Capture Photo`, `Queue Inspection`, `Sync All`, dropdown triggers) adhere strictly to $\ge 44 \times 44\text{ px}$.
  2. **Camera API Binding:** Verified `capture="environment"` attribute on file inputs to trigger direct rear-facing camera activation on native mobile operating systems.
  3. **Role Correction UI:** Dropdown selector allows post-capture role modification (`FRONT`, `BACK`, `SIDE`, `TOP`, `BOTTOM`, `CLOSE_UP`, `UNKNOWN`).
  4. **Queue Drawer:** Responsive slide-over drawer displays all queued items with badges (`QUEUED`, `SYNCING`, `FAILED`, `SYNCED`) and individual retry/discard buttons.

### 3.3 Physical Device Hardware Test Matrix (To Be Executed by Field Pilot Officers)
When physical hardware is available, pilot officers must execute and record outcomes in the following test matrix:

| Test ID | Target Device Model | OS & Browser Version | Test Procedure | Acceptance Criterion | Pilot Outcome / Defect |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **HW-01** | iPhone 14 / 15 / 16 | iOS 17.5+ / Mobile Safari | Open mobile URL over HTTPS; trigger camera. | Camera permission prompt appears; rear lens activates without page reload. | **PENDING FIELD PILOT** |
| **HW-02** | iPhone 14 / 15 / 16 | iOS 17.5+ / Mobile Safari | Capture glossy laminate pouch under supermarket fluorescent light. | Real-time quality preview flags glare $> 8\%$; retake guidance prompts tilt. | **PENDING FIELD PILOT** |
| **HW-03** | Google Pixel 7 / 8 / 9 | Android 14+ / Chrome Mobile | Capture cylindrical bottle label with macro autofocus at 15 cm. | Autofocus locks on fine text ($\ge 1.5\text{ mm}$); blur score $< 80$. | **PENDING FIELD PILOT** |
| **HW-04** | Samsung Galaxy S23/S24 | Android 14+ / Chrome Mobile | Reassign panel role from `SIDE` to `BACK` in pre-reliance review. | PATCH request executes; compliance re-evaluates within 500 ms. | **PENDING FIELD PILOT** |
| **HW-05** | Any Physical Device | Low battery ($< 15\%$) / OS Power Saver | Capture 5 consecutive commodities. | Browser tab does not crash from memory pressure during image staging. | **PENDING FIELD PILOT** |

---

## 4. Weak-Network & Deployment Behavior Verification

### 4.1 Offline Draft Creation & Queue Persistence
- **Storage Architecture:**
  - Implemented in [`frontend/src/components/MobileInspectionMode.jsx`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/frontend/src/components/MobileInspectionMode.jsx).
  - High-resolution panel photograph Blobs are stored in browser **IndexedDB** (`metricheck_offline_db` / object store `offline_drafts`), completely bypassing the 5 MB `localStorage` string quota.
  - Lightweight queue metadata is mirrored in `localStorage` under `metricheck_offline_queue_meta` for instant UI rendering on cold start.
- **Workflow & Queue Behavior:**
  - If `navigator.onLine === false` or upload times out, clicking **"Queue Offline Inspection"** persists the draft locally with status `QUEUED`.
  - Inspectors can queue dozens of packages consecutively while walking retail aisles without connectivity.

### 4.2 Sequential FIFO Resubmission & Weak-Network Timeout
- **Sequential Resubmission Worker (`syncOfflineQueue`):**
  - When connection is restored, tapping **"Sync All"** triggers sequential FIFO upload of pending drafts.
  - Drafts transition dynamically through statuses: `QUEUED` $\to$ `SYNCING` $\to$ `SYNCED` (or `FAILED`).
- **Weak-Network Timeout Resilience:**
  - A 35-second `AbortSignal` timeout is attached to each upload request.
  - If weak cellular coverage causes the connection to stall, the worker aborts the request, increments `retry_count`, marks the draft as `FAILED` with descriptive error (*"Upload timed out (weak signal). Tap retry."*), and continues without dropping queued data.
  - A dedicated **Retry** button allows individual draft resubmission.

### 4.3 Post-Capture Role Correction & Server Re-Evaluation
- **Endpoint:** `PATCH /api/scans/{scan_id}/images/{image_id}/role` implemented in [`backend/app/api/scans.py`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/app/api/scans.py#L225-L260).
- If an inspector discovers a mislabeled panel (e.g. front image mislabeled as back), changing the role re-triggers multi-image extraction and re-evaluates the compliance rule engine live without losing data.
- Verified by automated regression test [`test_role_update_triggers_compliance_reevaluation`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/backend/tests/test_real_package_validation.py#L842-L879).

### 4.4 HTTPS Deployment, PWA & Service Worker
- **PWA Manifest:** [`frontend/public/manifest.json`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/frontend/public/manifest.json) declares application name, theme color (`#1e3a8a`), standalone display mode, and responsive launcher icons.
- **Service Worker:** [`frontend/public/sw.js`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/frontend/public/sw.js) implements:
  - Cache-first strategy for static application shell (`index.html`, bundle scripts, styles).
  - Network passthrough with fallback for API requests.
  - Web Push event listener (`self.addEventListener('push', ...)`) supporting background inspection notifications.
- **Service Worker Registration:** [`frontend/src/main.jsx`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/frontend/src/main.jsx#L15-L27) registers the service worker conditioned on `window.isSecureContext` or `localhost`.
- **Deployment Prerequisites Tracked:**
  1. Valid SSL/TLS certificate (HTTPS) is mandatory for Service Worker registration, Web Push API, and Camera API permissions on non-localhost origins.
  2. VAPID keypair (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`) required in backend configuration before activating push broadcasts.
  3. No secrets exposed: VAPID private keys remain in server environment variables only.

---

## 5. System Health, Quality Gates & Milestone Closure

### 5.1 Verification Commands & Output Evidence

#### 1. Backend Real Package Validation Tests (36 tests)
```powershell
.venv/Scripts/python -m pytest tests/test_real_package_validation.py -v
```
- **Result:** **36 passed**, 2 warnings in **28.84s** (Exit code: `0`).
- **Evidence:** Verified dataset classification, manifest audit, split leakage detection, small-sample flags, presence taxonomy, and real photo refusal invariants.

#### 2. Complete Backend Test Suite (179 tests)
```powershell
.venv/Scripts/python -m pytest tests -q
```
- **Result:** **179 passed**, 2 warnings in **74.88s** (01:14) (Exit code: `0`).
- **Evidence:** 100% test pass rate across OCR, compliance engine, modular extractors, reliability stress fixtures, and visual compliance tests.

#### 3. Real Package Benchmark Runner
```powershell
.venv/Scripts/python tests/run_real_validation_benchmark.py
```
- **Result:** Exit code `0` in 72.84s.
- **Manifest Split Integrity:** `VERIFIED (0 Leaks)`.
- **Synthetic ECE:** `0.0313` (`CALIBRATED`).
- **Real Photo Benchmark Status:** `NOT EXECUTED — no verified genuine physical photographs supplied`.

#### 4. Frontend Code Quality (Oxlint)
```powershell
npm.cmd run lint
```
- **Result:** **0 errors**, 20 warnings (unused variables in pre-existing legacy pages: `AnalysisPage`, `RulesExplorerPage`, `NewScanPage`, `ResultsPage`) in **41ms**.

#### 5. Frontend Production Build (Vite v8.3.0)
```powershell
npm.cmd run build
```
- **Result:** Exit code `0` in **927ms**.
- **Bundle Assets:**
  - `dist/index.html`: `0.59 kB` (gzip: `0.36 kB`)
  - `dist/assets/index-BDzmH36K.css`: `42.33 kB` (gzip: `8.08 kB`)
  - `dist/assets/index-BAKmEap4.js`: `344.98 kB` (gzip: `97.09 kB`)

---

### 5.2 Milestone 15 Completion State: Partially Complete / Pilot Ready

In accordance with Milestone 15 acceptance criteria:

| Acceptance Criterion | Requirement | Empirical Status | Gate Verdict |
| :--- | :--- | :--- | :---: |
| **Genuine Dataset Validation** | Passes schema, provenance, annotation, and leakage checks | 0 real photos on disk; manifest audit flags missing files | **BLOCKED** |
| **Real-Photo Benchmark Execution** | Executed against verified genuine photographs | Benchmark officially marked **NOT EXECUTED** | **BLOCKED** |
| **Physical Hardware Device Pilot** | Verified on physical iPhone (Safari) and Android (Chrome) | Physical testbed hardware unavailable in CI environment | **BLOCKED** |
| **Deployment Readiness** | HTTPS, Service Worker, IndexedDB queue, 35s timeout | Active and verified in browser emulation & local build | **MET** |
| **System Integrity & Build** | 179 backend tests pass, 0 lint errors, production build ok | 179 passed (74.88s), 0 lint errors (41ms), build ok (927ms) | **MET** |

**Final Milestone 15 Verdict:** **Partially Complete (Pilot Ready — Field Validation Gates Kept Explicitly Open)**.

---

### 5.3 Prioritized Follow-Up Action Plan

| Priority | Task Description | Owner | Required Input / Dependency |
| :---: | :--- | :--- | :--- |
| **P1** | **Physical Package Photograph Acquisition**<br>Collect 50–100 physical retail commodities and photograph 150–350 multi-angle panels per [`DATA_COLLECTION_PACKAGE.md`](file:///c:/Users/ppran/OneDrive/Desktop/projects/dept_hack/MetriCheck/datasets/real_package_validation/DATA_COLLECTION_PACKAGE.md). | **Project Field Team**<br>(Delhi, Mumbai, Bengaluru, Pune) | Commercial retail purchase across pouches, cartons, bottles, blister packs, tins. |
| **P1** | **Human Annotation & Double Review**<br>Transcribe 12 fields, tag presence status, draw relative bounding boxes, and conduct dual-annotator verification ($\kappa \ge 0.85$). | **Annotation Team + Compliance Adjudicator** | Populated JSON files in `annotations/real/` conforming to `real_photo_manifest_template.json`. |
| **P1** | **Unblock Real-Photo Benchmark Run**<br>Execute `run_real_validation_benchmark.py` against populated real photos and record empirical field-level accuracy and calibration. | **Antigravity / Engineering Team** | Arrival of verified physical images in `images/real/`. |
| **P2** | **Physical Mobile Device Field Testing**<br>Execute test matrix HW-01 to HW-05 on physical iPhone (Safari) and Android (Chrome) to evaluate autofocus, glare tilt, and battery thermal behavior. | **Field Pilot Officers / QA** | Physical testbed smartphones on retail floor. |
| **P2** | **Production HTTPS & Push Deployment**<br>Deploy backend behind TLS reverse proxy (Nginx / Cloudflare) and configure VAPID keys for push notifications. | **DevOps / Infrastructure** | Server hosting environment, domain, SSL certificate. |
