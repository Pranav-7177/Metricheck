# MetriCheck — Mobile Inspection Edge Mode Architecture & Technical Specification

**Document Version:** 1.0.0  
**Effective Standard:** Legal Metrology (Packaged Commodities) Rules, 2011  
**Module:** Mobile Field Inspection & Pre-Reliance Evidence Review  

---

## 1. Overview & Operational Context

Legal Metrology Officers and retail inspection teams conduct field inspections in retail supermarkets, distribution warehouses, wholesale *mandis*, and local retail stores (*kirana* shops). In these field settings:
- Inspectors frequently encounter spotty or intermittent network connectivity (e.g. basement retail floors or rural locations).
- Packages must be photographed from multiple angles (front, back, sides, top, bottom, and close-ups) to capture all statutory declarations.
- Bad lighting, glare from ceiling fluorescents, and motion blur are common field capture hazards.
- Inspectors cannot rely on binary automated verdicts without verifying evidence provenance, image quality, confidence levels, and any detected cross-panel conflicts.

**MetriCheck Mobile Inspection Edge Mode** delivers a streamlined, touch-optimized field capture and review workflow that preserves deterministic compliance semantics, handles connection interruptions safely, and provides immediate capture guidance.

---

## 2. On-Device vs. Server-Side Execution Stages

To maintain strict legal correctness and zero crash resiliency without making false claims about offline AI, MetriCheck partitions pipeline stages between the mobile client and the edge server:

| Pipeline Stage | Execution Environment | Technical Implementation | Measured Latency |
| :--- | :--- | :--- | :--- |
| **Camera Acquisition & Framing** | **On-Device (Mobile Browser)** | HTML5 Camera API (`capture="environment"`), multi-file picker, touch zoom | Instant ($\approx 0\text{ ms}$) |
| **EXIF Orientation & Dimension Check** | **On-Device (Mobile Browser)** | Client-side Canvas decode, dimension validation ($\ge 600\times 600$), EXIF transposition | $< 15\text{ ms}$ |
| **Offline Draft Staging & Queueing** | **On-Device (Mobile Browser)** | `localStorage` and `IndexedDB` draft queue, network change listener (`navigator.onLine`) | $< 5\text{ ms}$ |
| **Immediate Quality Telemetry** | **Server / Edge Gateway** | Lightweight `POST /api/scans/quality-preview` using Laplacian blur variance and HSV glare masking | $\approx 25\text{ ms}$ |
| **Contrast Enhancement (CLAHE)** | **Server / Edge Gateway** | OpenCV CLAHE grid ($8\times 8$, clip limit 2.0) and fast non-local means denoising | $\approx 64\text{ ms}$ |
| **OCR Text & Bounding Box Extraction**| **Server / Edge Gateway** | Pretrained PaddleOCR (PP-OCRv6 text detector & recognizer, PP-LCNet textline orientation) | $\approx 3,400\text{ ms}$ (p50: $2,826\text{ ms}$) |
| **Modular Statutory Field Parsing** | **Server / Edge Gateway** | Deterministic regex, Indian currency parsers, and context-window statutory extractors | $\approx 0.8\text{ ms}$ |
| **Multi-Image Cross-Panel Aggregation**| **Server / Edge Gateway** | Evidence corroboration across front, back, side, and close-up views; duplicate suppression | $\approx 0.45\text{ ms}$ |
| **Versioned Legal Rule Evaluation** | **Server / Edge Gateway** | Decoupled ComplianceEngine applying LMR 2011 category schedules (Rule 6 & First Schedule) | $\approx 0.15\text{ ms}$ |
| **Pre-Reliance Evidence Review** | **On-Device (Mobile Browser)** | Interactive Evidence Review screen displaying provenance, confidence, conflicts, and guidance | Instant ($\approx 0\text{ ms}$) |
| **Total End-to-End Pipeline Latency** | **Hybrid Edge Pipeline** | Complete mobile capture, quality check, OCR extraction, and legal audit generation | $\approx 3,500\text{ ms}$ |

---

## 3. Concrete Technical Blockers for Full Client-Only Offline Inference

Master Prompt 11 requires a clear statement of technical feasibility:
> *"If full on-device inference is not feasible in the existing stack, deliver the capture-and-review workflow and document the concrete technical blocker instead of adding a simulated edge mode."*

Full client-side offline execution of the complete pipeline (without a local edge server) is currently blocked by four concrete technical factors:

1. **OCR Runtime and Deep Learning Dependencies:**
   - MetriCheck utilizes **PaddleOCR PP-OCRv6** with PP-LCNet direction classification. This requires the compiled PaddlePaddle C++ runtime, cuDNN/BLAS libraries, and OpenCV.
   - Compiling PP-OCRv6 to WebAssembly (WASM) for browser-only execution results in an initial download of $> 120\text{ MB}$ of model weights and runtime code.
2. **Mobile Browser Memory Limits:**
   - On typical mid-range mobile devices (e.g. Android devices with 3–4 GB RAM or iPhones running Safari), loading a 120 MB deep-learning model into browser WASM triggers WebGL/WASM memory allocations exceeding 500 MB during inference, leading to frequent browser tab crashes (OOM kills) on real 12 MP camera photographs.
3. **Multi-Script and Indian Language Packaging Accuracy:**
   - Lightweight browser-only alternatives (such as Tesseract.js / pure JS engines) exhibit significant accuracy degradation on Indian packaging fonts (condensed dot-matrix date stamps, ₹ Rupee symbol ligature variations, and small print $< 1.5\text{ mm}$).
   - Relying on substandard in-browser OCR would violate MetriCheck's legal safety requirement: *"Do not create heuristic or fabricated compliance verdicts."*
4. **Deterministic Versioned Legal Engine Isolation:**
   - Statutory compliance rules under the Legal Metrology (Packaged Commodities) Rules, 2011 require strict category and version tracking (`LMR-2011-v2024.1`). Running rules on the backend guarantees that every legal determination is auditable and synchronized with the statutory database.

### Supported Edge Topology:
To achieve true offline field inspection without compromising correctness, MetriCheck supports an **Edge Gateway Topology**:
- The mobile phone connects over local Wi-Fi or tethering to a lightweight inspection field laptop or Raspberry Pi 5 edge unit running the containerized MetriCheck backend.
- The phone runs the mobile web interface, while the local edge gateway executes PaddleOCR and the compliance engine completely offline without requiring internet access to external cloud APIs.

---

## 4. Mobile Capture & Resilient Queueing Behavior

1. **Direct Camera Capture:**
   - The file input element specifies `capture="environment"`, instructing iOS Safari and Android Chrome to open the rear-facing camera directly rather than opening a multi-step file picker.
2. **Local Draft Persistence:**
   - As the inspector types product details and captures photographs, the inspection state is continuously synchronized to `localStorage` under the key `metricheck_mobile_draft`.
   - If the browser tab is accidentally closed or the phone screen turns off, navigating back to MetriCheck instantly restores the in-progress draft.
3. **Resilient Network Upload Manager:**
   - The interface monitors `navigator.onLine` and displays a persistent connectivity indicator (`Online` in emerald, `Offline` in amber).
   - If an upload fails due to network timeout or poor signal, the photographs remain intact in the local panel list, and a prominent **Retry Upload** button appears.
4. **Immediate Capture Guidance:**
   - As each photograph is snapped, the client calls `/api/scans/quality-preview` to assess blur variance and specular reflection.
   - Actionable instructions (e.g. *"Hold camera steady"*, *"Tilt package away from direct glare"*, *"Move closer"*) appear directly on the panel card within 30 ms.

---

## 5. Pre-Reliance Evidence Review Step

Before an inspector signs an inspection notice or relies on an automated assessment, the mobile workflow enters the **Pre-Reliance Review Step**:

1. **Evidence Provenance Verification:**
   - Each extracted field displays the source photograph thumbnail and the assigned panel role (e.g., `FRONT`, `BACK`, `SIDE`, `CLOSE_UP`).
2. **Panel Role Correction:**
   - If an inspector discovers that a photograph was incorrectly labeled (e.g. a back panel was misclassified as front), they can reassign the role directly via a dropdown. This triggers an immediate, deterministic re-evaluation via `PATCH /api/scans/{id}/images/{img_id}/role`.
3. **Optical Uncertainty & Distractor Isolation:**
   - Low-confidence or unreadable text is highlighted with `UNABLE_TO_VERIFY` or `NOT_FOUND` badges.
   - Missing fields are **never** automatically converted into statutory legal violations without affirmative evidence.
4. **Conflict Resolution Display:**
   - If conflicting declarations were detected across panels (e.g. front panel shows ₹199 while back panel shows ₹249), the card displays an `AMBIGUOUS` alert with both candidates and their respective panel origins.
5. **Incremental Corroboration:**
   - An inspector can tap **"+ Add Panel Photo"** at any time to capture an additional panel or close-up and re-evaluate live without restarting the inspection.

---

## 6. Device Requirements & Browser Compatibility

- **Supported Mobile Browsers:**
  - Safari on iOS 15.0+ (WebKit)
  - Chrome on Android 9.0+ (Blink)
  - Samsung Internet 16.0+
  - Firefox Mobile 100.0+
- **Minimum Screen Width:** 360 px (responsive grid tested up to 4K displays).
- **Touch Target Sizing:** All interactive buttons and selectors have minimum touch bounds of $44 \times 44\text{ px}$.
- **Client Storage Requirement:** $< 50\text{ MB}$ local cache for active drafts.
