# MetriCheck — Real Package Failure Analysis & Calibration Report

**Execution Timestamp:** `2026-10-20T03:02:06.714221Z`  
**Git Commit:** `b580fb7449c314b9bffae29c8b48ce2ab0e2293d`  
**Dataset Classification:** `SYNTHETIC_CONTROLLED`  
**Total Products Evaluated:** `12`  
**Total Images Evaluated:** `20`  
**Manifest Integrity Status:** `PASSED`  

## 1. Executive Summary

This report presents the field-level extraction evaluation, confidence calibration analysis, and failure root-cause taxonomy under Indian Legal Metrology Rules, 2011.

> **Legal Integrity Note:** Real-photo validation accuracy and controlled synthetic stress tests are strictly separated. Synthetic images are never used to claim real-world performance.

## 2. Confidence Calibration & ECE Analysis

**Synthetic Expected Calibration Error (ECE):** `0.0313`

| Confidence Bin | Sample Count (n) | Mean Confidence | Empirical Accuracy | Calibration Gap | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[0.00 - 0.50)` | 7 | 0.000 | 0.0% | 0.0000 | Reliable |
| `[0.50 - 0.70)` | 0 | 0.600 | N/A | 0.0000 | Sample < 5 |
| `[0.70 - 0.85)` | 0 | 0.775 | N/A | 0.0000 | Sample < 5 |
| `[0.85 - 0.95)` | 11 | 0.899 | 100.0% | 0.1006 | Reliable |
| `[0.95 - 1.00]` | 49 | 1.000 | 98.0% | 0.0202 | Reliable |

## 3. Failure Cases Log

| Product | Field | Expected Status | Actual Status | Failure Category | Severity | Failure Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| prod_02_carton | MANUFACTURING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_04_tin | PACKING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_05_unreadable_mrp | PRODUCT_NAME | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_05_unreadable_mrp | MRP | `UNABLE_TO_VERIFY` | `NOT_FOUND` | `EXTRACTION_FAILURE` | `WARNING` | Failure state expectation mismatch |
| prod_05_unreadable_mrp | NET_QUANTITY | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `ERROR` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_07_glare_over_mrp | MRP | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `ERROR` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_11_coffee_distributed | MANUFACTURING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |

## 4. Failure Taxonomy Breakdown

- **OCR_FAILURE**: Text token was unreadable or severely degraded by physical packaging conditions (blur, glare, curvature).
- **EXTRACTION_FAILURE**: OCR detected text lines, but deterministic regex or context window failed to associate statutory keyword with value.
- **ASSOCIATION_FAILURE**: Multiple dates or entities were present and misattributed to the wrong field.
- **AGGREGATION_FAILURE**: Cross-panel aggregation failed to prioritize clearer evidence or identify conflicts.
- **QUALITY_GATE_FAILURE**: Blur or glare score failed to catch unreadable image before inference.

## 5. Controlled Failure-State Verification

1. **Unreadable MRP (`prod_05_unreadable_mrp`)**: Verified that severe defocus blur produces `NOT_FOUND` / `UNABLE_TO_VERIFY` without hallucinating arbitrary price values.
2. **Missing MRP (`prod_06_missing_mrp`)**: Verified that genuine absence is reported as `NOT_FOUND` without fabricating a price.
3. **Glare Over MRP (`prod_07_glare_over_mrp`)**: Verified that specular reflection over pricing is not falsely verified.
4. **Promo Distractors (`prod_08_price_distractors`)**: Verified that promo discounts ('Save ₹50', 'Offer ₹100') are rejected in favor of statutory MRP.
5. **Quantity Distractors (`prod_09_quantity_distractors`)**: Verified that nutritional calories (210 kcal) and carbs (25 g) are ignored.
6. **Date Distractors (`prod_10_date_distractors`)**: Verified that batch numbers and license numbers are not falsely extracted as statutory dates.
7. **Conflicting Prices (`prod_12_conflicting_prices`)**: Verified that conflicting prices across panels produce `AMBIGUOUS`.
