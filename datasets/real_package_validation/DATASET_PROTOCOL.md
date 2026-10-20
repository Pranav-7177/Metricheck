# MetriCheck — Real-World Packaging Dataset Protocol
## SIH26034: Legal Metrology Packaged Commodities Compliance Scanner

**Document Version:** 1.0.0  
**Effective Standard:** Legal Metrology (Packaged Commodities) Rules, 2011 (as amended 2024)  
**Dataset Target:** 25–50 Physical Indian Retail Packaged Commodities  

---

## 1. Executive Summary & Purpose

This protocol establishes the standardized, reproducible methodology for collecting, curating, photographing, and human-annotating a benchmark dataset of physical Indian retail commodities.

MetriCheck assists Legal Metrology officers and packaging compliance teams in verifying statutory declarations required under **Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011**. Evaluating MetriCheck against real physical packaging requires rigorous validation on genuine retail photographs reflecting realistic shelf, lighting, surface curvature, and print quality conditions.

> **CRITICAL LEGAL INVARIANT:** Controlled synthetic images and programmatic perturbance tests serve for algorithmic stress-testing only. They **must never** be reported or presented as real-world packaging evidence. A validation benchmark run is labeled `REAL_PHOTO` **if and only if** it evaluates verified genuine photographs of physical retail commodities.

---

## 2. Dataset Composition & Stratification (25–50 Commodities)

The curated catalog must contain a balanced, representative cross-section of physical products commonly sold in Indian retail stores, supermarkets, and local grocers (*kirana* stores):

### 2.1 Statutory Category Distribution
1. **Packaged Food & Beverages (35–40%, ~10–18 products):**
   - Staples (atta, rice, pulses, sugar, salt)
   - Biscuits, confectionery, snacks, and edible oils
   - Ready-to-drink beverages and dairy cartons/pouches
2. **Cosmetics & Personal Care (30–35%, ~8–15 products):**
   - Soaps, shampoos, hair oils, creams, lotions
   - Toothpaste, deodorants, perfumes
3. **Household Products & Chemicals (25–30%, ~7–12 products):**
   - Laundry detergents (powders, bars, liquids)
   - Surface cleaners, dishwash liquids, disinfectants
   - Batteries, shoe polish, mosquito repellents

### 2.2 Packaging Form Factor Distribution
To rigorously evaluate surface geometry and optical distortion, the catalog must span:
- **Pouches & Flexible Poly/Foil (35–40%):** Heat-sealed pillow pouches, gusseted pouches, metallized laminates prone to crinkling, specular reflections, and folds over declarations.
- **Folding Cartons & Paperboard Boxes (30–35%):** Planar rectangular surfaces with crisp printing, but with potential flap creases and corner folds.
- **Bottles, Jars & Rigid Containers (25–30%):** Cylindrical or tapered glass/PET/HDPE surfaces producing cylindrical perspective distortion and curved label reflections.
- **Tins & Tubes (Optional ~5–10%):** Metallic crimped ends and cylindrical metal surfaces.

### 2.3 Panel Roles & Photographic Angles per Commodity
Each physical commodity should be photographed across all accessible panels bearing statutory declarations:
- **`FRONT` (Principal Display Panel - PDP):** Brand name, product generic name, net quantity, and front-facing MRP/USP where applicable.
- **`BACK` (Information / Statutory Panel):** Full manufacturer/packer/importer name and address, consumer care details, ingredients/composition.
- **`SIDE` / `LEFT_SIDE` / `RIGHT_SIDE`:** Month/year of manufacture/packing, batch number, nutritional facts, bar code, secondary declarations.
- **`TOP` / `BOTTOM`:** Stamped date and price lines (e.g. on bottle caps, tin lids, or bottom seams).
- **`CLOSE_UP`:** High-magnification macro photographs of small declarations, unit sale price (USP), or fine-print statutory text (e.g. font height < 1.5mm) to test resolution limits.

---

## 3. Photographic Acquisition Guidelines

To ensure realistic, consistent, and untampered image capture:

1. **Capture Devices:** Modern commercial smartphones (minimum 12 MP sensor, standard optical focal length ~24–28mm equivalent).
2. **Lighting Protocols:**
   - **Diffuse Natural/Ambient (60% of captures):** Indirect room lighting simulating standard retail or office inspection desks.
   - **Direct Fluorescent/Overhead (20% of captures):** Simulating retail shelf environments with potential specular glare on glossy plastic.
   - **Challenging/Low-Light (20% of captures):** Simulating warehouse or backroom inspection (minimum 50 lux).
3. **Framing & Orientation:**
   - The package panel should occupy 70–90% of the image frame with a 5–15% surrounding margin.
   - Camera lens held perpendicular (±10°) to the target panel.
   - Natural unrotated capture; EXIF orientation flags must accurately reflect camera orientation.
4. **Resolution & Format:**
   - Minimum resolution: 1200 × 1200 pixels (JPEG, PNG, or WebP).
   - Uncompressed or high-quality compression (JPEG quality $\ge 90$).
   - No computational bokeh, artificial beauty filters, or synthetic text overlays.

---

## 4. Privacy, Redaction, and Licensing Expectations

1. **No Personal Identifiable Information (PII):**
   - Photographs must capture exclusively retail merchandise packaging.
   - No individual faces, store staff names, personal payment cards, customer identification, or customer addresses may be stored in the dataset.
   - In accordance with the Legal Metrology Act, corporate commercial addresses of registered manufacturers, packers, and importers are statutory public disclosures and are preserved without modification.
2. **Commercial Sourcing & Transparency:**
   - Physical packages must be acquired through legitimate commercial retail purchases in India.
   - Store name, retail receipt details, and individual cashier identifiers must **not** be recorded in the public dataset.
3. **Licensing:**
   - Dataset metadata and ground-truth annotations are provided under open evaluation terms for non-commercial academic research and compliance bench-testing.
   - Physical trademarks, trade dress, and brand logos remain the exclusive intellectual property of their respective manufacturers.

---

## 5. Ground-Truth Annotation Protocol

### 5.1 Evaluated Statutory Declarations (12 Standard Fields)
Ground-truth annotations cover the 12 fields evaluated by MetriCheck under LMR 2011:
1. `PRODUCT_NAME` — Generic/common name and commodity description.
2. `MRP` — Maximum Retail Price including statutory tax phrase (*"inclusive of all taxes"*).
3. `NET_QUANTITY` — Standardized metric net quantity (strictly prohibiting non-standard terms such as *"when packed"*).
4. `MANUFACTURER` — Complete registered name and geographic address of manufacturer.
5. `PACKER` — Name and address of packaging facility (if different from manufacturer).
6. `IMPORTER` — Name and address of registered Indian importer (for imported goods).
7. `MANUFACTURING_DATE` — Month and year of manufacture.
8. `PACKING_DATE` — Month and year of packing.
9. `EXPIRY_DATE` — Expiry date where applicable.
10. `BEST_BEFORE` — Best before advisory period.
11. `CONSUMER_CARE` — Consumer complaint officer telephone, email, and postal address.
12. `COUNTRY_OF_ORIGIN` — Country of origin declaration (mandatory for all commodities).

### 5.2 Ground-Truth Declaration Status Taxonomy
To avoid conflating absence with illegibility or OCR failures, each declaration in ground truth must be tagged with one of five explicit physical presence states:

| Status | Meaning | Benchmark Accounting |
| :--- | :--- | :--- |
| `LEGIBLE` | Physically present on packaging and fully readable by human annotator. Contains exact ground truth string. | Evaluated for extraction accuracy (Correct vs. Incorrect vs. Not Found). |
| `ILLEGIBLE` | Physically present on package (e.g., faint dot-matrix stamp, smudged ink, thermal fade), but human annotator cannot decipher characters with certainty. | System expected to report `UNABLE_TO_VERIFY` or `LOW_CONFIDENCE`. Never counted as an extraction error if unverified. |
| `OBSCURED` | Physically present on package, but occluded by a fold, crimp, seal, sticker, or glare reflection. | System expected to report `UNABLE_TO_VERIFY`. Never penalized as a missing declaration. |
| `ABSENT` | Declaration physically does not exist on any panel of the physical packaging. | System expected to report `NOT_FOUND`. |
| `NOT_APPLICABLE` | Declaration is legally not required for this commodity under LMR 2011 (e.g. `IMPORTER` on indigenous Indian products, `EXPIRY_DATE` on non-perishable hardware). | Excluded from mandatory extraction denominator. |

### 5.3 Bounding Box & Coordinate Format
Where spatial annotations are captured, ground truth specifies relative coordinates normalized to $[0.0, 1.0]$:
```json
"bounding_box": {
  "x_rel": 0.125,
  "y_rel": 0.650,
  "w_rel": 0.450,
  "h_rel": 0.085
}
```

### 5.4 Multi-Annotator Review & Adjudication Protocol
1. **Primary Annotation:** Annotator 1 transcribes declarations, tags presence status, and marks image panel roles.
2. **Independent Sample Verification:** A randomly selected subset ($\ge 20\%$ of commodities) is independently double-annotated by Annotator 2 without seeing Annotator 1's transcriptions.
3. **Inter-Annotator Agreement Metric:**
   - Raw character-level and field-level agreement percentage is calculated across the sample.
   - Cohen's Kappa ($\kappa$) is computed for categorical presence status (`LEGIBLE`, `ILLEGIBLE`, `OBSCURED`, `ABSENT`, `NOT_APPLICABLE`). Target agreement: $\kappa \ge 0.85$.
4. **Dispute Adjudication:** Any discrepant fields between Annotator 1 and Annotator 2 are reviewed by a Senior Compliance Specialist/Adjudicator, who examines the physical package directly under magnification. The adjudicated value is recorded as authoritative ground truth.

---

## 6. Product-Level Split Integrity (Zero Cross-Panel Leakage)

If any catalog tuning, parameter calibration, or train/validation/test splits are performed:
- **Split assignment MUST be made at the product level**, never at the image level.
- All panel photographs (front, back, side, close-up) of product `real_prod_05` must reside exclusively within the same split partition.
- Cross-panel contamination where the front panel is in the training split and the back panel is in the evaluation split is **strictly prohibited**.

---

## 7. Metric Reporting and Denominator Integrity

For every benchmark execution on real photographs:
1. Every reported accuracy percentage **MUST** include its exact numerator and denominator:
   $$\text{Extraction Accuracy} = \frac{\text{Correct}}{\text{Correct} + \text{Incorrect} + \text{Not Found} + \text{Unverified}} \quad (\text{sample count } n)$$
2. Small sample warnings are mandatory whenever a sub-category or field has fewer than 5 valid ground-truth instances ($n < 5$).
3. **Extraction accuracy** (did OCR and regex find the text?) is reported independently from **compliance rule outcomes** (did the product satisfy LMR Rule 6?).
4. Confidence calibration is reported across discrete probability bins with empirical accuracy and Expected Calibration Error (ECE).
