# MetriCheck — Real-Photo Pilot Data-Collection Package & Acceptance Protocol
## SIH26034: Legal Metrology Packaged Commodities Compliance Scanner

**Document Version:** 1.0.0 (Milestone 13)  
**Effective Standard:** Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011 (as amended 2024)  
**Status of Real-Photo Validation:** **NOT EXECUTED** (Pending Genuine Field Photographs)  
**Target Catalog Size:** 50–100 Physical Retail Commodities (150–350 multi-angle photographs)

---

## 1. Executive Blocker Statement & Validation Invariant

As of Milestone 13, `datasets/real_package_validation/images/real` contains **zero (0) physical image files** (only `.gitkeep`), and `annotations/real` contains **zero (0) ground-truth files**. The ten (10) entries declared in `dataset_manifest.json` under `real_catalog_specification` represent catalog requirements whose 28 referenced image files (`real_prod_01_front.jpg`, etc.) are missing from disk, lack spatial bounding boxes, and each commodity category and panel role has $n < 5$ samples.

> ### **CRITICAL LEGAL & SCIENTIFIC INVARIANT**
> - In strict accordance with Master Prompt 12 and Milestone 13, MetriCheck **REFUSES to claim real-world validation** until verified genuine photographs are supplied.
> - Synthetic stress fixtures (12 commodities) evaluate algorithmic resilience under controlled blur, glare, and distractors, but **MUST NEVER** be presented as real-world evidence.
> - The real-photo benchmark remains explicitly marked **NOT EXECUTED** with this document defining the complete data-collection package required to unblock execution.

---

## 2. Target Catalog Stratification Matrix (50–100 Commodities)

To achieve statistical validity ($n \ge 5$ across all primary categories, packaging geometries, and panel roles), the field collection team must acquire **50 to 100 commercially purchased Indian retail commodities**:

### 2.1 Commodity Category Stratification ($n \ge 12$ per category)
1. **Food & Grocery (35–40%, 20–35 products):**
   - Whole flours (atta, maida, besan), basmati rice, pulses (*toor dal*, *chana dal*)
   - Edible oils (pouch, PET bottle, tin), ghee (carton, jar)
   - Biscuits, cookies, confectionery, namkeen, potato chips, extruded snacks
   - Tea, coffee, spices (whole, powdered), table salt, sugar
   - Dairy products (pasteurized milk pouches, paneer, curd, UHT cartons)
2. **Cosmetics & Personal Care (25–30%, 15–25 products):**
   - Bathing soaps (paper-wrapped, duplex cartons), handwashes (dispenser bottles)
   - Shampoos, conditioners, hair oils (rigid PET/HDPE bottles)
   - Toothpaste (laminated collapsible tubes inside folding cartons)
   - Skin creams, lotions (jars, tubes, pump bottles)
   - Talcum powders, deodorants (pressurized aerosol cans, plastic containers)
3. **Household Products & Chemicals (20–25%, 10–20 products):**
   - Laundry detergent powders (LDPE/metallized pouches, cardboard boxes)
   - Detergent bars (flow-wrapped poly), liquid detergents (handled jerry cans)
   - Surface cleaners, toilet cleaners, dishwashing bars/gels (HDPE squeeze bottles)
   - Mosquito repellents (liquid vaporizers, aerosols), air fresheners
4. **General & Hardware Commodities (10–15%, 5–15 products):**
   - Batteries (blister cards), LED bulbs (folding cartons), adhesives, shoe care

### 2.2 Packaging Form Factors & Materials
- **Flexible Pouches (Pillow, Gusset, Stand-Up Zipper) (30–35%):** Evaluate handling of wrinkles, creases across fine print, and specular foil glare.
- **Folding Cartons & Duplex Paperboard Boxes (25–30%):** Standard planar surfaces with flap creases and edge shadows.
- **Cylindrical Plastic Bottles (PET / HDPE) (20–25%):** Evaluate radial text distortion on curved surfaces and vertical date stamps.
- **Glass Bottles & Jars (5–10%):** Transparency, back-label bleed-through, and specular reflections.
- **Metallic Tins & Cans (5–10%):** Crimped seams, bottom batch stamping, metallic reflectance.
- **Blister Packs & Backing Cards (5–10%):** Plastic thermoformed blisters covering printed card declarations.
- **Collapsible Flexible Tubes (5–10%):** Crimped bottom dates, curved tube surfaces.

### 2.3 Photographic Coverage per Commodity (3–5 Panels)
Every physical commodity must be photographed across all panels bearing statutory disclosures:
- **`front` (Principal Display Panel - PDP):** Commodity identity, brand name, net quantity, USP (where front-facing).
- **`back` (Information / Statutory Panel):** Complete manufacturer/packer/importer identity, customer care, ingredient details.
- **`side` / `left_side` / `right_side`:** Date of manufacture/packing, batch number, nutritional panel, FSSAI / legal licenses.
- **`top` / `bottom`:** Cap, lid, or bottom seal stamps (mandatory if date or MRP is stamped on lid or base).
- **`close_up`:** High-magnification capture of small text (font height $< 1.5\text{ mm}$), dot-matrix stamps, or MRP clusters.

---

## 3. Photographic Acquisition Protocols

### 3.1 Equipment & Camera Settings
- **Permissible Devices:** Modern commercial smartphones (minimum 12 MP sensor, f/1.8–f/2.4 aperture, optical image stabilization recommended).
- **Resolution:** Minimum $1200 \times 1200\text{ pixels}$ (preferred: native 12 MP $4032 \times 3024$ or 24 MP).
- **Format:** Uncompressed PNG, high-quality JPEG ($Q \ge 90$), or WebP ($Q \ge 90$).
- **Lens Cleanliness:** Ensure physical camera lens is wiped clean of fingerprints prior to every capture session.
- **Prohibited Modes:** No portrait/bokeh mode, computational beauty smoothing, artificial HDR tone-mapping, or digital zoom $> 1.0\times$.

### 3.2 Lighting Protocols
- **Diffuse Natural Daylight (60% of dataset):** Indirect window daylight or soft diffused indoor lighting ($300–500\text{ lux}$).
- **Retail Fluorescent Overhead (25% of dataset):** Direct overhead supermarket/shop lighting ($200–400\text{ lux}$) producing realistic specular glare on flexible laminate and glossy plastic.
- **Low-Light / Backroom ($15\%$ of dataset):** Simulating warehouse or storeroom conditions ($50–150\text{ lux}$) to test camera sensitivity and noise resilience.

### 3.3 Framing, Angle, and Calibration
- **Fill Ratio:** The target package panel must occupy $70\%\text{ to }90\%$ of the image frame with a $5\%\text{ to }15\%$ safety margin.
- **Perspective Angle:** Camera optical axis held perpendicular ($\pm 10^\circ$) to the panel. Avoid extreme oblique angles unless evaluating known perspective distortion.
- **Calibration Reference:** For commodities with fine print, include a calibrated visual reference in the same focal plane (e.g. Standard ID-1 card width: $85.60\text{ mm}$, or standard ₹5 coin diameter: $23.00\text{ mm}$) to validate millimeter font height verification.

### 3.4 PII & Privacy Regulations
- **Strict Prohibition:** Photographs must capture **exclusively retail merchandise packaging**.
- **No Human Subjects:** No human faces, store personnel, customer clothing, or biometric features may be visible.
- **No Financial Data:** Payment card numbers, credit slips, cash register receipts, or internal shop inventory barcodes must not appear.
- **Statutory Public Disclosures:** In accordance with the Legal Metrology Act, commercial corporate addresses and consumer care phone/email declared on packaging are statutory public disclosures and are transcribed without alteration.

---

## 4. Annotation Guide for the 12 Statutory Fields (LMR 2011)

| Field Identifier | Statutory Requirement (Rule 6) | Ground-Truth Transcription Rules |
| :--- | :--- | :--- |
| `PRODUCT_NAME` | Generic name and commodity description. | Exact common/generic name (e.g. *"Refined Sunflower Oil"*, *"Whole Wheat Atta"*). Brand name may precede if part of statutory declaration. |
| `MRP` | Maximum Retail Price inclusive of all taxes. | Must include currency symbol and mandatory tax phrasing (e.g. *"₹ 245.00 (Incl. of all taxes)"*). Separate USP if declared alongside. |
| `NET_QUANTITY` | Standard metric net quantity. | Must include numeric value and statutory SI unit (e.g. *"5 kg"*, *"1 L (910 g)"*, *"500 g"*, *"100 ml"*). Strictly exclude non-standard terms (*"when packed"*). |
| `MANUFACTURER` | Full legal name and registered address of manufacturing premises. | Complete name, street/plot, city, state, and 6-digit PIN code. |
| `PACKER` | Name and address of packing facility (if different from manufacturer). | Record if distinct packer is declared. If manufacturer and packer are identical, mark `NOT_APPLICABLE`. |
| `IMPORTER` | Name and address of registered Indian importer (for imported goods). | Mandatory for imported goods. For indigenous domestic Indian manufacture, mark `NOT_APPLICABLE`. |
| `MANUFACTURING_DATE` | Month and year of manufacture. | Standardized format `MM/YYYY` or `MM/YY` (e.g. *"03/2026"*). If full date declared (e.g. 15/03/2026), record as printed. |
| `PACKING_DATE` | Month and year of packaging (if distinct from manufacture). | Record if declared. If manufacturing date is declared and packing date is omitted, mark `NOT_APPLICABLE`. |
| `EXPIRY_DATE` | Expiration date for commodities subject to spoilage. | Record exact date / month / year as declared. |
| `BEST_BEFORE` | Best before duration or period. | Transcribe full advisory text (e.g. *"Best Before 9 Months from Manufacture"*). |
| `CONSUMER_CARE` | Consumer complaint redressal contact details. | Must transcribe all available channels: Officer designation, toll-free phone number, email address, and postal address. |
| `COUNTRY_OF_ORIGIN` | Country where commodity was manufactured/produced. | Mandatory declaration (e.g. *"India"*, *"Made in India"*, *"Country of Origin: Vietnam"*). |

---

## 5. Ground-Truth Presence Status Taxonomy

Every field in the ground-truth annotation must declare one of the five mutually exclusive presence states:

1. **`LEGIBLE`:** Declaration is physically present on the packaging and fully readable by human annotators without optical ambiguity. Evaluated for character-level and semantic extraction accuracy.
2. **`ILLEGIBLE`:** Declaration is physically present on the package, but degraded by faint ink, smudged dot-matrix print, thermal paper fading, or physical scuffing such that human annotators cannot decipher characters with certainty.  
   *Accounting Rule:* MetriCheck is expected to report `UNABLE_TO_VERIFY` or `LOW_CONFIDENCE`. It is **never** penalized as an extraction failure if the system declines to guess.
3. **`OBSCURED`:** Declaration is physically present on the package, but occluded by a foil fold, gusset crease, seam seal, retail security sticker, or specular glare spot.  
   *Accounting Rule:* MetriCheck is expected to report `UNABLE_TO_VERIFY` and highlight panel retake guidance.
4. **`ABSENT`:** Declaration is physically missing from all panels of the physical container.  
   *Accounting Rule:* If MetriCheck reports `NOT_FOUND`, it is scored as `CORRECT` (proper absence detection). If MetriCheck hallucinates a value, it is scored as `INCORRECT`.
5. **`NOT_APPLICABLE`:** Declaration is legally exempt for this commodity category under LMR 2011 (e.g. `IMPORTER` on domestic goods, `EXPIRY_DATE` on non-perishable soap).  
   *Accounting Rule:* Excluded from the mandatory extraction denominator. If MetriCheck reports `NOT_FOUND`, it is scored as `NOT_APPLICABLE`.

---

## 6. Spatial Bounding Box Specification

For spatial validation, each detected or ground-truth field must be annotated with relative coordinates normalized to $[0.0, 1.0]$:
```json
"bounding_box": {
  "x_rel": 0.125,
  "y_rel": 0.650,
  "w_rel": 0.450,
  "h_rel": 0.085
}
```
- $x_{\text{rel}}$: Horizontal distance from left edge to top-left corner of text box, divided by total image width ($0.0 \le x_{\text{rel}} \le 1.0$).
- $y_{\text{rel}}$: Vertical distance from top edge to top-left corner of text box, divided by total image height ($0.0 \le y_{\text{rel}} \le 1.0$).
- $w_{\text{rel}}$: Width of text box, divided by total image width ($0.0 < w_{\text{rel}} \le 1.0$).
- $h_{\text{rel}}$: Height of text box, divided by total image height ($0.0 < h_{\text{rel}} \le 1.0$).
- Coordinates must satisfy $x_{\text{rel}} + w_{\text{rel}} \le 1.0$ and $y_{\text{rel}} + h_{\text{rel}} \le 1.0$.

---

## 7. Multi-Annotator Adjudication Workflow

To ensure ground-truth integrity and prevent single-annotator bias:

```
[Physical Package Captured]
            │
            ▼
┌─────────────────────────┐
│ Primary Annotation      │  (Annotator 1 transcribes text, tags presence,
│ (100% of Catalog)       │   draws spatial bounding boxes)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Independent Double Read │  (Annotator 2 independently re-transcribes
│ (≥ 20% Random Sample)   │   blind sample without viewing Annotator 1)
└───────────┬─────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────┐
│ Inter-Annotator Agreement Check                        │
│ - Presence Taxonomy: Cohen's Kappa κ ≥ 0.85            │
│ - Exact String Match: Agreement ≥ 95%                  │
└───────────┬────────────────────────────────────────────┘
            │
      Discrepancies?
      ├── YES ──► ┌──────────────────────────────────────┐
      │           │ Senior Legal Metrology Specialist    │
      │           │ Physical Package Inspection Review   │
      │           │ (Authoritative Adjudicated Record)   │
      │           └──────────────────────────────────────┘
      │                             │
      └── NO ───────────────────────┴──► [Approved Ground Truth Manifest]
```

---

## 8. Automated Acceptance Checklist & Validation Gatekeeper

Before any dataset package can be accepted into `datasets/real_package_validation/`:

- [ ] **Physical Image Existence:** Every image file referenced in the manifest exists in `datasets/real_package_validation/images/real/` and is decodable as a valid image ($\ge 1200\times 1200\text{ px}$).
- [ ] **Zero Synthetic Contamination:** SHA-256 hashes of real images do not match any synthetic stress fixtures.
- [ ] **Zero Cross-Split Leakage:** All panel photographs of a commodity reside strictly in the same split (`train`, `val`, or `test`). No image file or SHA-256 hash appears across split boundaries.
- [ ] **Sample Size Sufficiency:** Minimum 50 distinct commodities. Every statutory category has $n \ge 5$ commodities. Every major role (`front`, `back`, `side`, `top`, `close_up`) has $n \ge 5$ images.
- [ ] **Schema Conformance:** JSON files validate against `datasets/real_package_validation/metadata/dataset_schema.json` with zero schema errors.
- [ ] **Presence Taxonomy Compliance:** 100% of ground-truth declarations specify one of the five valid states: `LEGIBLE`, `ILLEGIBLE`, `OBSCURED`, `ABSENT`, or `NOT_APPLICABLE`.
- [ ] **Bounding Box Normalization:** All spatial bounding boxes adhere to relative $[0.0, 1.0]$ bounds with positive width and height.
- [ ] **Zero PII Verification:** No human faces, credit cards, or cashier slips are present in any photograph.

---

## 9. Required Inputs from the Project Team

To unblock the real-photo validation benchmark, the project team must deliver:

| Deliverable Item | Description | Target Destination |
| :--- | :--- | :--- |
| **Physical Photographs** | 150–350 multi-panel images of 50–100 retail commodities in JPG/PNG/WebP format ($\ge 1200\times 1200$). | `datasets/real_package_validation/images/real/` |
| **Populated Manifest** | JSON manifest using `real_photo_manifest_template.json` specifying product metadata, camera device, lighting, and splits. | `datasets/real_package_validation/metadata/dataset_manifest.json` |
| **Annotated Ground Truth** | Human-verified ground-truth JSON files for each commodity with 12 fields, presence states, and bounding boxes. | `datasets/real_package_validation/annotations/real/<product_id>.json` |
| **Dual-Review Log** | Verification report signed by two annotators and senior adjudicator confirming Cohen's $\kappa \ge 0.85$. | Included in manifest `multi_annotator_review` blocks. |
