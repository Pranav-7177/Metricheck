import React, { useState } from 'react';
import { 
  ShieldCheck, AlertTriangle, CheckCircle2, HelpCircle, 
  ArrowLeft, Download, Printer, RefreshCw, Eye, 
  Scale, Tag, Info, AlertOctagon, FileText, Calendar,
  Upload, Layers, Copy, Check, Camera
} from 'lucide-react';
import StatusBadge from '../components/StatusBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import QualityBadge from '../components/QualityBadge';

export default function ResultsPage({ scan, onBack, onRefresh }) {
  const [activeTab, setActiveTab] = useState("rules"); // default to rules to highlight compliance
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evalError, setEvalError] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadRole, setUploadRole] = useState("BACK");
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [updatingRoleId, setUpdatingRoleId] = useState(null);

  const handleUpdateImageRole = async (imageId, newRole) => {
    setUpdatingRoleId(imageId);
    try {
      const formData = new FormData();
      formData.append("role", newRole);
      const res = await fetch(`/api/scans/${scan.id}/images/${imageId}/role`, {
        method: "PATCH",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update panel role.");
      }
      if (onRefresh) await onRefresh();
    } catch (e) {
      alert(e.message);
    } finally {
      setUpdatingRoleId(null);
    }
  };

  if (!scan) {
    return (
      <div className="p-8 text-center text-slate-500">
        <p>No scan selected or report not found.</p>
        <button onClick={onBack} className="mt-4 text-blue-600 underline font-semibold text-sm">
          Return to Dashboard
        </button>
      </div>
    );
  }

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setEvalError(null);
    try {
      const res = await fetch(`/api/scans/${scan.id}/evaluate`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Evaluation failed.");
      }
      if (onRefresh) {
        await onRefresh();
      }
    } catch (e) {
      setEvalError(e.message);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleUploadPanel = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append("image", uploadFile);
      formData.append("role", uploadRole);

      const res = await fetch(`/api/scans/${scan.id}/images`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed.");
      }
      setShowUploadModal(false);
      setUploadFile(null);
      if (onRefresh) {
        await onRefresh();
      }
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setIsUploading(false);
    }
  };

  const declarations = scan.declarations || [];
  const rules = scan.latest_evaluation?.results || scan.rule_results || [];
  const evaluation = scan.latest_evaluation;
  const images = scan.images || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-lg border border-slate-200 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs transition-colors cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5 text-blue-600" />
            <span>Add Panel Photo</span>
          </button>

          <button
            onClick={handleEvaluate}
            disabled={isEvaluating}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-3 py-1.5 rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? "animate-spin" : ""}`} />
            <span>{isEvaluating ? "Evaluating..." : "Re-evaluate Rules"}</span>
          </button>

          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {evalError && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{evalError}</span>
        </div>
      )}

      {/* Primary Executive Verdict Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xs space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-slate-100 pb-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
                {scan.category_name || "General Packaged Commodity"}
              </span>
              <span className="text-xs text-slate-400 font-mono">Scan ID #{scan.id}</span>
              {scan.is_demo && (
                <span className="px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-bold">
                  DEMO AUDIT RECORD
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              {scan.product_name}
            </h1>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Calendar className="w-3.5 h-3.5" />
              <span>Inspection Timestamp: {new Date(scan.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Verdict Badge & Score Box */}
          <div className="flex sm:flex-col items-center sm:items-end justify-between gap-3 shrink-0 bg-slate-50 sm:bg-transparent p-4 sm:p-0 rounded-xl">
            <StatusBadge status={scan.overall_status} size="lg" />
            <div className="text-right">
              <span className="text-xs text-slate-500 font-medium">Compliance Score</span>
              <div className="text-2xl font-bold font-mono text-slate-900">
                {scan.compliance_score}%
              </div>
            </div>
          </div>
        </div>

        {/* Summary Verdict Note */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>Official Inspection Assistance Assessment</span>
          </div>
          <p className="text-sm text-slate-800 leading-relaxed font-medium">
            {scan.summary_verdict || "Assessment completed."}
          </p>

          <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
            <div className="flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Measurement Status: <strong>{scan.is_calibrated ? "Calibrated against known reference" : "Estimated distance heuristic"}</strong>
              </span>
            </div>
            <span className="italic text-slate-400">
              * Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011
            </span>
          </div>
        </div>
      </div>

      {/* Upload Panel Photo Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Add Package Panel Photograph</h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Upload a photograph of another package panel (back, side, top, or close-up) to corroborate declarations and extend coverage without losing existing evidence.
            </p>

            <form onSubmit={handleUploadPanel} className="space-y-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Panel Role / Type</label>
                <select
                  value={uploadRole}
                  onChange={(e) => setUploadRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white text-slate-800 text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="BACK">Back Information Panel</option>
                  <option value="SIDE">Side Panel (General)</option>
                  <option value="LEFT_SIDE">Left Side Panel</option>
                  <option value="RIGHT_SIDE">Right Side Panel</option>
                  <option value="TOP">Top Panel</option>
                  <option value="BOTTOM">Bottom Panel</option>
                  <option value="CLOSE_UP">Close-up Declaration View</option>
                  <option value="FRONT">Front / Principal Display Panel</option>
                  <option value="UNKNOWN">Unknown / Other Panel</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Select Photograph</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs text-slate-700 file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  required
                />
              </div>

              {uploadError && (
                <div className="bg-rose-50 border border-rose-200 rounded-lg p-2.5 text-xs text-rose-800 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || isUploading}
                  className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs"
                >
                  {isUploading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>{isUploading ? "Uploading & Re-evaluating..." : "Upload & Re-evaluate"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Scan Evidence Reliability & Coverage Section */}
      {(scan.scan_reliability || scan.coverage_summary) && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Evidence Reliability & Package Coverage
              </h2>
            </div>
            {scan.scan_reliability?.reliability_level && (
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold font-mono border ${
                scan.scan_reliability.reliability_level === "HIGH"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : scan.scan_reliability.reliability_level === "MODERATE"
                  ? "bg-blue-50 text-blue-700 border-blue-200"
                  : scan.scan_reliability.reliability_level === "REVIEW_REQUIRED"
                  ? "bg-purple-50 text-purple-700 border-purple-200"
                  : "bg-amber-50 text-amber-700 border-amber-200"
              }`}>
                RELIABILITY: {scan.scan_reliability.reliability_level}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60 space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Photographic Usability
              </span>
              <p className="font-semibold text-slate-900 text-sm">
                {scan.scan_reliability?.image_usability_summary || `${images.length} images evaluated`}
              </p>
              {scan.coverage_summary?.degraded_images_count > 0 && (
                <p className="text-[11px] text-amber-700">
                  {scan.coverage_summary.degraded_images_count} image(s) degraded but safely evaluated
                </p>
              )}
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60 space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Panels Inspected
              </span>
              <div className="flex flex-wrap gap-1.5 pt-0.5">
                {scan.coverage_summary?.known_panel_roles?.length > 0 ? (
                  scan.coverage_summary.known_panel_roles.map((r) => (
                    <span key={r} className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-mono text-[10px] font-bold">
                      {r}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500 italic">No specific panel labels</span>
                )}
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60 space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                Duplicate Filtering
              </span>
              <p className="font-semibold text-slate-900 text-sm">
                {scan.coverage_summary?.duplicate_images_count > 0
                  ? `${scan.coverage_summary.duplicate_images_count} duplicate(s) filtered`
                  : "No duplicates detected"}
              </p>
              <p className="text-[10px] text-slate-500">
                Duplicates are preserved for audit but excluded from independent corroboration.
              </p>
            </div>
          </div>

          {/* Actionable Next Step & Limitations */}
          <div className="bg-slate-50/70 p-3.5 rounded-xl border border-slate-200/60 text-xs space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800">Reliability Assessment: </strong>
                <span className="text-slate-700">
                  {scan.scan_reliability?.reliability_message || "Evidence evaluated across all uploaded package photographs."}
                </span>
              </div>
            </div>

            {scan.scan_reliability?.coverage_limitations && (
              <div className="text-slate-600 pl-6 text-[11px]">
                <strong>Coverage Note: </strong> {scan.scan_reliability.coverage_limitations}
              </div>
            )}

            {scan.scan_reliability?.recommended_next_action && (
              <div className="flex items-start gap-2 text-emerald-800 bg-emerald-50/80 p-2.5 rounded-lg border border-emerald-100">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-emerald-900">Recommended Next Step: </strong>
                  <span>{scan.scan_reliability.recommended_next_action}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("declarations")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "declarations"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Extracted Declarations</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {declarations.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("rules")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "rules"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Rule Verifications & Explainability</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {rules.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("images")}
          className={`pb-3 relative cursor-pointer ${
            activeTab === "images"
              ? "text-blue-700 font-bold border-b-2 border-blue-600"
              : "text-slate-500 hover:text-slate-900"
          }`}
        >
          <span>Packaging Photographs & Quality</span>
          <span className="ml-2 px-1.5 py-0.5 rounded-full bg-slate-100 text-[11px] text-slate-600">
            {images.length}
          </span>
        </button>
      </div>

      {/* Tab Content: Extracted Declarations */}
      {activeTab === "declarations" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Statutory Package Declarations</h3>
              <p className="text-xs text-slate-500">Extracted fields, OCR confidences, and physical font measurements</p>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              Threshold: 55% confidence
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {declarations.map((decl) => (
              <div key={decl.id || decl.field_name} className="p-5 space-y-3 hover:bg-slate-50/50 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900">{decl.display_name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono uppercase">
                        {decl.field_name}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono uppercase">
                        {decl.source_image_role} panel
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {decl.has_conflict && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-bold uppercase tracking-wider">
                        Conflict
                      </span>
                    )}
                    <StatusBadge status={decl.extraction_status || decl.status} size="sm" />
                  </div>
                </div>

                {/* Detected Value & OCR Snippet */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/60 space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">Detected Value:</span>
                    <p className="font-semibold text-slate-900 text-sm">
                      {decl.detected_value || (
                        (decl.extraction_status === "UNABLE_TO_VERIFY" || decl.status === "UNABLE_TO_VERIFY") ? (
                          <span className="text-amber-600 italic">Unreadable / Unable to Verify</span>
                        ) : (decl.extraction_status === "AMBIGUOUS" || decl.status === "REVIEW_REQUIRED") ? (
                          <span className="text-purple-600 italic">Ambiguous / Conflicting Values</span>
                        ) : (decl.extraction_status === "LOW_CONFIDENCE") ? (
                          <span className="text-amber-600 italic">Low Confidence Detection</span>
                        ) : (
                          <span className="text-slate-400 italic">Not Detected</span>
                        )
                      )}
                    </p>
                  </div>

                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/60 space-y-1">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase">Raw OCR String:</span>
                    <p className="font-mono text-slate-700 break-all text-xs">
                      {decl.raw_ocr_snippet || <span className="text-slate-400 italic">No text extracted</span>}
                    </p>
                  </div>
                </div>

                {/* Visual Verification & Calibration Evidence */}
                {(() => {
                  const visEv = decl.visual_evidence || (decl.evidence && decl.evidence.visual_evidence);
                  if (!visEv) return null;

                  const statusBadges = {
                    MEASURABLE: "bg-emerald-50 text-emerald-700 border-emerald-200",
                    READABLE_ONLY: "bg-blue-50 text-blue-700 border-blue-200",
                    NOT_MEASURABLE: "bg-slate-100 text-slate-700 border-slate-200",
                    UNABLE_TO_VERIFY: "bg-amber-50 text-amber-700 border-amber-200",
                    AMBIGUOUS: "bg-purple-50 text-purple-700 border-purple-200"
                  };

                  return (
                    <div className="bg-slate-50/80 rounded-xl border border-slate-200 p-4 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/60 pb-2">
                        <div className="flex items-center gap-2">
                          <Eye className="w-4 h-4 text-blue-600" />
                          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                            Visual Evidence & Calibration Verification
                          </span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${statusBadges[visEv.visual_status] || "bg-slate-100 text-slate-600"}`}>
                          STATUS: {visEv.visual_status || "NOT_MEASURABLE"}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-xs">
                        <div className="bg-white p-2.5 rounded-lg border border-slate-200/60">
                          <span className="text-[10px] font-semibold text-slate-500 uppercase block">Raw Text Height</span>
                          <span className="font-mono font-bold text-slate-800 text-sm">
                            {visEv.text_height_px ? `${visEv.text_height_px.toFixed(1)} px` : "—"}
                          </span>
                        </div>

                        <div className="bg-white p-2.5 rounded-lg border border-slate-200/60">
                          <span className="text-[10px] font-semibold text-slate-500 uppercase block">Physical Height</span>
                          {visEv.font_height_mm !== null && visEv.font_height_mm !== undefined ? (
                            <span className="font-mono font-bold text-emerald-700 text-sm">
                              {visEv.font_height_mm.toFixed(1)} mm
                            </span>
                          ) : (
                            <span className="font-sans font-medium text-slate-500 text-xs italic">
                              Not measurable
                            </span>
                          )}
                        </div>

                        <div className="bg-white p-2.5 rounded-lg border border-slate-200/60">
                          <span className="text-[10px] font-semibold text-slate-500 uppercase block">Calibration Reference</span>
                          <span className="font-mono text-slate-700 text-xs">
                            {visEv.calibration_method ? visEv.calibration_method.replace(/_/g, " ") : "UNCALIBRATED"}
                          </span>
                          {visEv.calibration_confidence > 0 && (
                            <span className="text-[10px] text-slate-400 block font-mono">
                              Conf: {Math.round(visEv.calibration_confidence * 100)}%
                            </span>
                          )}
                        </div>

                        <div className="bg-white p-2.5 rounded-lg border border-slate-200/60">
                          <span className="text-[10px] font-semibold text-slate-500 uppercase block">Visibility & Placement</span>
                          <span className="font-semibold text-slate-800 text-xs block">
                            {visEv.visibility || "FULLY_VISIBLE"}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">
                            Region: {visEv.placement || "CENTER"}
                          </span>
                        </div>
                      </div>

                      {/* Readability & Quality Factors */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-slate-200/60">
                        <span>Readability: <strong className="text-slate-900">{visEv.readability || "READABLE"}</strong></span>
                        <span className="text-slate-300">|</span>
                        <span>Blur Variance: <strong className="font-mono text-slate-900">{visEv.blur_score ? Math.round(visEv.blur_score) : "—"}</strong></span>
                        <span className="text-slate-300">|</span>
                        <span>Glare Overlap: <strong className="font-mono text-slate-900">{visEv.glare_overlap_percentage !== undefined ? `${visEv.glare_overlap_percentage.toFixed(1)}%` : "0%"}</strong></span>
                        {visEv.perspective_score < 0.70 && (
                          <>
                            <span className="text-slate-300">|</span>
                            <span className="text-amber-700 font-medium">Perspective Distortion Detected</span>
                          </>
                        )}
                      </div>

                      {/* Explanation or Operational Guidance */}
                      {visEv.explanation && (
                        <p className="text-xs text-slate-600 italic bg-amber-50/50 p-2 rounded border border-amber-200/40">
                          {visEv.explanation}
                        </p>
                      )}
                      {visEv.recommendation && (
                        <div className="flex items-center gap-1.5 text-xs text-blue-800 bg-blue-50/60 p-2 rounded border border-blue-200/50 font-medium">
                          <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span>Actionable Guidance: {visEv.recommendation}</span>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Uncertainty & Measurement Indicators */}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-1 text-xs border-t border-slate-100">
                  <div className="w-full sm:w-auto">
                    <ConfidenceBar confidence={decl.confidence} />
                  </div>


                  {decl.estimated_font_height_mm && (
                    <div className="flex items-center gap-3 text-slate-600">
                      <div className="flex items-center gap-1">
                        <Scale className="w-3.5 h-3.5 text-blue-600" />
                        <span>Estimated Font Height:</span>
                        <strong className="font-mono text-slate-900">{decl.estimated_font_height_mm} mm</strong>
                      </div>
                      <span className="text-slate-300">|</span>
                      <span className="text-slate-500">
                        Statutory Min: <strong className="font-mono">{decl.required_font_height_mm} mm</strong>
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        decl.measurement_confidence === "VERIFIED" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                      }`}>
                        {decl.measurement_confidence}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content: Rule Verifications */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          {/* Executive Evaluation Summary Metrics Bar */}
          {evaluation?.summary && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-blue-600" />
                  <span className="font-bold text-slate-900 text-sm">Deterministic Compliance Evaluation</span>
                  <span className="text-xs text-slate-400">({evaluation.total_rules} Statutory Rules Evaluated)</span>
                </div>
                <StatusBadge status={evaluation.overall_status} size="md" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200">
                  <div className="text-lg font-bold text-emerald-700">{evaluation.summary.passed_rules ?? evaluation.passed_rules}</div>
                  <div className="text-[11px] font-semibold text-emerald-800 uppercase">PASS</div>
                </div>
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200">
                  <div className="text-lg font-bold text-rose-700">{evaluation.summary.failed_rules ?? evaluation.failed_rules}</div>
                  <div className="text-[11px] font-semibold text-rose-800 uppercase">FAIL</div>
                </div>
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200">
                  <div className="text-lg font-bold text-amber-700">{evaluation.summary.warning_rules ?? evaluation.warning_rules}</div>
                  <div className="text-[11px] font-semibold text-amber-800 uppercase">WARNING</div>
                </div>
                <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="text-lg font-bold text-blue-700">{evaluation.summary.not_verifiable_rules ?? evaluation.not_verifiable_rules}</div>
                  <div className="text-[11px] font-semibold text-blue-800 uppercase">NOT VERIFIABLE</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="text-lg font-bold text-slate-700">{evaluation.summary.not_applicable_rules ?? evaluation.not_applicable_rules}</div>
                  <div className="text-[11px] font-semibold text-slate-600 uppercase">NOT APPLICABLE</div>
                </div>
                <div className="p-2.5 rounded-lg bg-purple-50 border border-purple-200">
                  <div className="text-lg font-bold text-purple-700">{evaluation.summary.critical_errors ?? evaluation.critical_errors ?? 0}</div>
                  <div className="text-[11px] font-semibold text-purple-800 uppercase">CRITICAL FAIL</div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-900">
            <p className="font-semibold">Legal Metrology Compliance Guarantee</p>
            <p className="text-blue-800 mt-0.5">
              Rule severity (CRITICAL, ERROR, WARNING, INFO) and compliance status (PASS, FAIL, WARNING, NOT_VERIFIABLE, NOT_APPLICABLE) are strictly decoupled. Missing or blurry declarations are marked NOT_VERIFIABLE and are never fabricated into premature legal violations.
            </p>
          </div>

          <div className="space-y-3">
            {rules.map((rule, idx) => {
              const severity = rule.severity || "ERROR";
              const severityClasses = {
                CRITICAL: "bg-red-100 text-red-800 border-red-200",
                ERROR: "bg-amber-100 text-amber-800 border-amber-200",
                WARNING: "bg-yellow-100 text-yellow-800 border-yellow-200",
                INFO: "bg-slate-100 text-slate-700 border-slate-200"
              }[severity] || "bg-slate-100 text-slate-700 border-slate-200";

              const fieldLabel = (rule.field_name || rule.field_target || "Declaration").toUpperCase();
              const ruleSource = rule.rule_source || rule.rule_reference || "APPROVED_RULE_REFERENCE";

              return (
                <div key={rule.id || rule.rule_id || idx} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">
                          {fieldLabel} Check
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${severityClasses}`}>
                          SEVERITY: {severity}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-mono font-semibold border border-blue-200">
                          {ruleSource}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 font-mono">
                        Rule ID: {rule.rule_id}
                      </div>
                    </div>

                    <StatusBadge status={rule.status} size="md" />
                  </div>

                  {/* Values & Evidence Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                      <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Detected Packaging Value:</span>
                      <p className="font-semibold text-slate-900">{rule.detected_value || rule.field_value || <span className="text-slate-400 italic">Not Detected</span>}</p>
                      {rule.normalized_value && rule.normalized_value !== rule.detected_value && (
                        <p className="text-[11px] text-slate-500 mt-1">Normalized: <span className="font-mono font-semibold text-slate-700">{rule.normalized_value}</span></p>
                      )}
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                      <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">Evidence & Traceability:</span>
                      {rule.evidence && Object.keys(rule.evidence).length > 0 ? (
                        <div className="text-[11px] text-slate-600 space-y-0.5">
                          {rule.evidence.source_ocr_ids && (
                            <p>Source OCR IDs: <span className="font-mono text-slate-800">{JSON.stringify(rule.evidence.source_ocr_ids)}</span></p>
                          )}
                          {rule.evidence.has_conflict && (
                            <p className="text-amber-700 font-semibold">Multiple conflicting detections found on package</p>
                          )}
                          {rule.evidence.bounding_box && (
                            <p>Box: <span className="font-mono text-slate-700">{JSON.stringify(rule.evidence.bounding_box)}</span></p>
                          )}
                        </div>
                      ) : (
                        <p className="text-slate-400 italic">No OCR box coordinates mapped</p>
                      )}
                    </div>
                  </div>

                  {/* Conflict alert when has_conflict is true */}
                  {rule.evidence?.has_conflict && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold text-amber-800">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                        <span>Conflicting Candidates Detected (Rule Evaluated as NOT_VERIFIABLE)</span>
                      </div>
                      <p className="text-amber-800">
                        System detected multiple conflicting declarations across panels. Compliance status is strictly set to NOT_VERIFIABLE rather than arbitrarily picking one candidate.
                      </p>
                      {rule.evidence.alternate_candidates && (
                        <p className="font-mono text-[11px] text-amber-700 mt-1">
                          Alternates: {rule.evidence.alternate_candidates.map(a => a.value || a.raw_value).join(", ")}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Statutory Reason & Suggested Action */}
                  <div className="bg-slate-50/70 p-3 rounded-lg border border-slate-200/60 text-xs space-y-1.5">
                    <div className="flex items-start gap-2">
                      <Info className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-slate-800">Reason / Finding: </strong>
                        <span className="text-slate-700">{rule.reason || rule.message}</span>
                      </div>
                    </div>

                    {rule.suggested_action && (
                      <div className="flex items-start gap-2 text-emerald-800 bg-emerald-50/70 p-2 rounded border border-emerald-100">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-emerald-900">Recommended Action: </strong>
                          <span>{rule.suggested_action}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab Content: Packaging Images & Quality */}
      {activeTab === "images" && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="text-base font-bold text-slate-900">Uploaded Packaging Photographs</h3>
            <p className="text-xs text-slate-500">Computer-vision quality assessments (sharpness, glare, lighting, resolution)</p>
          </div>

          {images.length === 0 ? (
            <p className="text-xs text-slate-500">No images linked to this scan.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {images.map((img) => (
                <div key={img.id} className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50/50">
                  <div className="p-3 border-b border-slate-200 bg-white flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <label className="text-[10px] font-bold text-slate-400 uppercase">Role:</label>
                        <select
                          value={(img.image_type || img.image_role || "FRONT").toUpperCase()}
                          disabled={updatingRoleId === img.id}
                          onChange={(e) => handleUpdateImageRole(img.id, e.target.value)}
                          className="px-2 py-0.5 text-xs font-bold bg-slate-50 border border-slate-300 rounded text-slate-800 uppercase cursor-pointer hover:bg-white"
                          title="Assign or correct panel role"
                        >
                          <option value="FRONT">FRONT</option>
                          <option value="BACK">BACK</option>
                          <option value="SIDE">SIDE</option>
                          <option value="LEFT_SIDE">LEFT_SIDE</option>
                          <option value="RIGHT_SIDE">RIGHT_SIDE</option>
                          <option value="TOP">TOP</option>
                          <option value="BOTTOM">BOTTOM</option>
                          <option value="CLOSE_UP">CLOSE_UP</option>
                          <option value="UNKNOWN">UNKNOWN</option>
                        </select>
                        {updatingRoleId === img.id && <RefreshCw className="w-3 h-3 text-blue-600 animate-spin" />}
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {img.resolution_w}x{img.resolution_h}px
                      </span>
                      {img.ocr_engine_used && (
                        <span className="text-[10px] font-mono bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-semibold">
                          {img.ocr_engine_used}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {img.preprocessing_status === "APPLIED" && (
                        <span className="text-[10px] font-medium bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5 rounded">
                          CLAHE Preprocessed
                        </span>
                      )}
                      <QualityBadge
                        status={img.quality_status}
                        blurScore={img.blur_score}
                        glareScore={img.glare_score}
                      />
                    </div>
                  </div>

                  <div className="aspect-video bg-black/5 flex items-center justify-center p-2">
                    <img
                      src={img.file_path}
                      alt={img.original_filename}
                      className="max-h-56 w-auto object-contain rounded-md"
                      onError={(e) => {
                        // Fallback placeholder
                        e.target.onerror = null;
                        e.target.src = "https://placehold.co/600x400/e2e8f0/475569?text=Packaging+Image+Preview";
                      }}
                    />
                  </div>

                  <div className="p-3 bg-white border-t border-slate-200 text-xs text-slate-600 space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="font-semibold text-slate-700">Quality Decision: </span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${
                          img.quality_decision === "UNSUITABLE"
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : img.quality_decision === "DEGRADED"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        }`}>
                          {img.quality_decision || "ACCEPTABLE"}
                        </span>
                        <span className="ml-2 text-slate-600">{img.quality_notes || "Adequate resolution and contrast for OCR."}</span>
                      </div>
                      {img.ocr_detections_count !== undefined && (
                        <span className="text-[11px] font-mono text-slate-500">
                          {img.ocr_detections_count} text token{img.ocr_detections_count === 1 ? '' : 's'} (avg conf: {Math.round((img.ocr_confidence || 0) * 100)}%)
                        </span>
                      )}
                    </div>

                    {/* Duplicate Detection Alert */}
                    {img.is_duplicate && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-[11px] text-amber-900 space-y-1">
                        <div className="flex items-center gap-1.5 font-bold text-amber-800">
                          <Copy className="w-3.5 h-3.5 text-amber-600" />
                          <span>Duplicate Relationship Detected ({img.duplicate_type || "EXACT"})</span>
                        </div>
                        <p>{img.duplicate_reason || "Matches another photograph in this scan."}</p>
                        <p className="text-[10px] text-amber-700 italic">
                          Preserved for auditability; not treated as independent corroboration.
                        </p>
                      </div>
                    )}

                    {/* Actionable Retake Guidance */}
                    {img.retake_guidance && img.retake_guidance.length > 0 && (
                      <div className="bg-blue-50/70 border border-blue-200 rounded-lg p-2.5 text-[11px] text-blue-900 space-y-1">
                        <span className="font-bold text-blue-800 flex items-center gap-1">
                          <Camera className="w-3.5 h-3.5 text-blue-600" />
                          Actionable Retake Instructions:
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-700">
                          {img.retake_guidance.map((g, idx) => (
                            <li key={idx}>{g}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* OCR Recovery Details */}
                    {img.ocr_attempt_count > 1 && (
                      <div className="text-[10px] font-mono bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded inline-block">
                        OCR Recovery: Attempt {img.ocr_attempt_count} with preprocessing applied
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
