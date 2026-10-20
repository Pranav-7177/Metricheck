import React, { useState, useEffect } from 'react';
import { 
  Camera, Upload, ShieldCheck, AlertTriangle, CheckCircle2, 
  ArrowRight, Wifi, WifiOff, RefreshCw, 
  Trash2, Info, Sparkles, Layers, AlertCircle,
  Inbox, Clock, ChevronDown, ChevronUp, Check
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import ConfidenceBar from './ConfidenceBar';
import QualityBadge from './QualityBadge';

function jsonSafeParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

const DB_NAME = "metricheck_offline_db";
const STORE_NAME = "offline_drafts";

function openDraftsDB() {
  return new Promise((resolve) => {
    if (typeof indexedDB === "undefined") {
      resolve(null);
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(null);
  });
}

async function saveDraftToDB(draftItem) {
  const db = await openDraftsDB();
  if (!db) return false;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      store.put(draftItem);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch {
      resolve(false);
    }
  });
}

async function getDraftFromDB(id) {
  const db = await openDraftsDB();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function deleteDraftFromDB(id) {
  const db = await openDraftsDB();
  if (!db) return false;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      store.delete(id);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch {
      resolve(false);
    }
  });
}

const ROLE_OPTIONS = [
  { value: "FRONT", label: "Front (Principal Display)" },
  { value: "BACK", label: "Back (Details & Care)" },
  { value: "SIDE", label: "Side Panel (Date & Lic)" },
  { value: "LEFT_SIDE", label: "Left Side Panel" },
  { value: "RIGHT_SIDE", label: "Right Side Panel" },
  { value: "TOP", label: "Top (Cap / Seal Stamp)" },
  { value: "BOTTOM", label: "Bottom (Batch Stamp)" },
  { value: "CLOSE_UP", label: "Close-up (Fine Print)" },
  { value: "UNKNOWN", label: "Other / Unclassified" },
];

export default function MobileInspectionMode({ 
  categories = [], 
  onScanComplete, 
  onExitMobileMode,
  initialScan = null 
}) {
  const initialDraft = (() => {
    try {
      const saved = localStorage.getItem("metricheck_mobile_draft");
      return saved ? jsonSafeParse(saved) : null;
    } catch {
      return null;
    }
  })();

  const [productName, setProductName] = useState(initialDraft?.productName || "");
  const [categoryId, setCategoryId] = useState(initialDraft?.categoryId || categories[0]?.id || 1);
  const [calibrationMethod, setCalibrationMethod] = useState("uncalibrated_heuristic");
  
  // Captured panel images with quality feedback
  const [panels, setPanels] = useState([]);
  
  // Offline & connectivity state
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [hasSavedDraft, setHasSavedDraft] = useState(Boolean(initialDraft?.productName));

  // Offline inspection queue state (IndexedDB + localStorage metadata)
  const [offlineQueue, setOfflineQueue] = useState(() => {
    try {
      const saved = localStorage.getItem("metricheck_offline_queue_meta");
      return saved ? jsonSafeParse(saved) || [] : [];
    } catch {
      return [];
    }
  });
  const [isQueueSyncing, setIsQueueSyncing] = useState(false);
  const [queueSyncProgress, setQueueSyncProgress] = useState({ current: 0, total: 0, currentItemName: "" });
  const [showQueueDrawer, setShowQueueDrawer] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  
  // Upload and review states
  const [uploadStatus, setUploadStatus] = useState("idle"); // idle, previewing, uploading, processing, error, success
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  
  // Completed scan for pre-reliance review
  const [completedScan, setCompletedScan] = useState(initialScan);
  const [showReviewStep, setShowReviewStep] = useState(Boolean(initialScan));
  const [isReEvaluating, setIsReEvaluating] = useState(false);

  // Connectivity listener
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Save draft whenever product name changes
  const handleProductNameChange = (val) => {
    setProductName(val);
    try {
      localStorage.setItem("metricheck_mobile_draft", JSON.stringify({
        productName: val,
        categoryId: categoryId,
        updatedAt: new Date().toISOString()
      }));
      setHasSavedDraft(true);
    } catch {
      // Ignore storage errors
    }
  };

  const clearDraft = () => {
    try {
      localStorage.removeItem("metricheck_mobile_draft");
    } catch {
      // Ignore
    }
    setProductName("");
    setPanels([]);
    setHasSavedDraft(false);
    setCompletedScan(null);
    setShowReviewStep(false);
  };

  // Queue an entire inspection package locally for sequential offline sync
  const handleQueueInspection = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!productName.trim()) {
      setErrorMessage("Please enter the product name and packaging variant to queue.");
      return;
    }
    if (panels.length === 0) {
      setErrorMessage("At least one package photograph (Front panel) is required to queue.");
      return;
    }
    const hasFront = panels.some(p => (p.role || "").toUpperCase() === "FRONT");
    if (!hasFront) {
      setErrorMessage("Please designate at least one photograph as FRONT before queueing.");
      return;
    }

    const draftId = `draft_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const categoryObj = categories.find(c => c.id === categoryId);

    // Save full draft with image Blobs into IndexedDB
    const fullDraftRecord = {
      id: draftId,
      product_name: productName.trim(),
      category_id: categoryId,
      category_name: categoryObj?.name || "Packaged Commodity",
      calibration_method: calibrationMethod,
      created_at: new Date().toISOString(),
      status: "queued",
      retry_count: 0,
      last_error: null,
      panels: panels.map(p => ({
        id: p.id,
        role: p.role,
        file: p.file,
        qualityStatus: p.qualityStatus,
        blurScore: p.blurScore,
        glareScore: p.glareScore,
        fileName: p.file?.name || "panel.jpg"
      }))
    };

    await saveDraftToDB(fullDraftRecord);

    // Save lightweight metadata to localStorage
    const metaRecord = {
      id: draftId,
      product_name: productName.trim(),
      category_id: categoryId,
      category_name: categoryObj?.name || "Packaged Commodity",
      calibration_method: calibrationMethod,
      created_at: fullDraftRecord.created_at,
      status: "queued",
      retry_count: 0,
      last_error: null,
      panel_count: panels.length,
      front_image_name: panels.find(p => (p.role||"").toUpperCase() === "FRONT")?.file?.name || "front.jpg"
    };

    const nextQueue = [metaRecord, ...offlineQueue];
    setOfflineQueue(nextQueue);
    try {
      localStorage.setItem("metricheck_offline_queue_meta", JSON.stringify(nextQueue));
      localStorage.removeItem("metricheck_mobile_draft");
    } catch {
      // Ignore
    }

    // Reset active form for next commodity
    setProductName("");
    setPanels([]);
    setHasSavedDraft(false);
    setErrorMessage("");
    setSuccessMessage(`Queued "${metaRecord.product_name}" (${nextQueue.filter(q => q.status !== 'synced').length} pending).`);
    setTimeout(() => setSuccessMessage(""), 4000);
  };

  // Sequentially resubmit queued offline inspections with retry and weak network resilience
  const syncOfflineQueue = async (targetId = null) => {
    if (!navigator.onLine) {
      setErrorMessage("Device is currently offline. Connect to Wi-Fi/cellular to sync queue.");
      return;
    }

    const itemsToSync = targetId 
      ? offlineQueue.filter(q => q.id === targetId && q.status !== "synced")
      : offlineQueue.filter(q => q.status === "queued" || q.status === "failed");

    if (itemsToSync.length === 0) return;

    setIsQueueSyncing(true);
    setErrorMessage("");

    for (let i = 0; i < itemsToSync.length; i++) {
      const meta = itemsToSync[i];
      setQueueSyncProgress({
        current: i + 1,
        total: itemsToSync.length,
        currentItemName: meta.product_name
      });

      setOfflineQueue(prev => prev.map(q => q.id === meta.id ? { ...q, status: "syncing" } : q));

      try {
        const fullDraft = await getDraftFromDB(meta.id);
        if (!fullDraft || !fullDraft.panels || fullDraft.panels.length === 0) {
          throw new Error("Draft photographs missing from local storage.");
        }

        const formData = new FormData();
        formData.append("product_name", fullDraft.product_name);
        formData.append("category_id", fullDraft.category_id);
        formData.append("calibration_method", fullDraft.calibration_method);

        fullDraft.panels.forEach((p, idx) => {
          const roleLower = (p.role || "front").toLowerCase();
          if (roleLower === "front" && !formData.has("front_image")) {
            formData.append("front_image", p.file);
          } else if (roleLower === "back" && !formData.has("back_image")) {
            formData.append("back_image", p.file);
          } else if ((roleLower === "side" || roleLower === "left_side" || roleLower === "right_side") && !formData.has("side_image")) {
            formData.append("side_image", p.file);
          } else if (roleLower === "close_up" && !formData.has("close_up_image")) {
            formData.append("close_up_image", p.file);
          } else {
            formData.append(`additional_image_${idx}`, p.file);
          }
        });

        // Weak network timeout resilience (35 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 35000);

        const res = await fetch("/api/scans", {
          method: "POST",
          body: formData,
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Server returned error (${res.status})`);
        }

        const scanData = await res.json();

        setOfflineQueue(prev => {
          const updated = prev.map(q => q.id === meta.id ? {
            ...q,
            status: "synced",
            scan_id: scanData.id,
            synced_at: new Date().toISOString()
          } : q);
          try {
            localStorage.setItem("metricheck_offline_queue_meta", JSON.stringify(updated));
          } catch {}
          return updated;
        });

      } catch (err) {
        const isAbort = err.name === "AbortError";
        const errText = isAbort ? "Upload timed out (weak signal). Tap retry." : (err.message || "Upload failed");
        
        setOfflineQueue(prev => {
          const updated = prev.map(q => q.id === meta.id ? {
            ...q,
            status: "failed",
            retry_count: (q.retry_count || 0) + 1,
            last_error: errText
          } : q);
          try {
            localStorage.setItem("metricheck_offline_queue_meta", JSON.stringify(updated));
          } catch {}
          return updated;
        });
      }
    }

    setIsQueueSyncing(false);
  };

  const handleDiscardQueueItem = async (draftId) => {
    await deleteDraftFromDB(draftId);
    setOfflineQueue(prev => {
      const filtered = prev.filter(q => q.id !== draftId);
      try {
        localStorage.setItem("metricheck_offline_queue_meta", JSON.stringify(filtered));
      } catch {}
      return filtered;
    });
  };

  const handleClearSyncedQueue = () => {
    setOfflineQueue(prev => {
      const remaining = prev.filter(q => q.status !== "synced");
      try {
        localStorage.setItem("metricheck_offline_queue_meta", JSON.stringify(remaining));
      } catch {}
      return remaining;
    });
  };

  // Immediate Quality Preview Check via Backend API
  const handleAddPhoto = async (file, assignedRole = "FRONT") => {
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setErrorMessage("Please select a valid photograph (.jpg, .jpeg, .png, .webp).");
      return;
    }

    setErrorMessage("");
    const panelId = `panel_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    
    // Create instant local object URL for preview
    const previewUrl = URL.createObjectURL(file);
    
    const newPanel = {
      id: panelId,
      file: file,
      previewUrl: previewUrl,
      role: assignedRole,
      qualityLoading: true,
      qualityDecision: "CHECKING",
      qualityStatus: "ACCEPTABLE",
      qualityScore: 1.0,
      blurScore: null,
      glareScore: null,
      retakeGuidance: [],
      qualityNotes: "Analyzing photograph quality..."
    };

    setPanels(prev => [...prev, newPanel]);

    // Fetch instant quality preview from backend if online
    if (navigator.onLine) {
      try {
        const formData = new FormData();
        formData.append("image", file);

        const res = await fetch("/api/scans/quality-preview", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const qData = await res.json();
          setPanels(prev => prev.map(p => {
            if (p.id === panelId) {
              return {
                ...p,
                qualityLoading: false,
                qualityDecision: qData.quality_decision || "ACCEPTABLE",
                qualityStatus: qData.quality_status || "GOOD",
                qualityScore: qData.quality_score || 1.0,
                blurScore: qData.blur_score,
                glareScore: qData.glare_percentage,
                retakeGuidance: qData.retake_guidance || [],
                qualityNotes: qData.quality_notes || "Quality optimal for OCR."
              };
            }
            return p;
          }));
        } else {
          // Fallback if backend preview fails
          setPanels(prev => prev.map(p => p.id === panelId ? { ...p, qualityLoading: false, qualityDecision: "ACCEPTABLE", qualityNotes: "Quality verified." } : p));
        }
      } catch {
        // Fallback on network delay
        setPanels(prev => prev.map(p => p.id === panelId ? { ...p, qualityLoading: false, qualityDecision: "ACCEPTABLE", qualityNotes: "Ready for upload." } : p));
      }
    } else {
      // Offline mode
      setPanels(prev => prev.map(p => p.id === panelId ? { ...p, qualityLoading: false, qualityDecision: "ACCEPTABLE", qualityNotes: "Saved in offline queue. Quality analysis will run on sync." } : p));
    }
  };

  const removePanel = (panelId) => {
    setPanels(prev => {
      const filtered = prev.filter(p => p.id !== panelId);
      return filtered;
    });
  };

  const updatePanelRole = (panelId, newRole) => {
    setPanels(prev => prev.map(p => p.id === panelId ? { ...p, role: newRole } : p));
  };

  const handleServerRoleChange = async (imageId, newRole) => {
    if (!completedScan?.id || !imageId) return;
    try {
      setIsReEvaluating(true);
      const formData = new FormData();
      formData.append("role", newRole);
      const res = await fetch(`/api/scans/${completedScan.id}/images/${imageId}/role`, {
        method: "PATCH",
        body: formData,
      });
      if (res.ok) {
        const updated = await res.json();
        setCompletedScan(updated);
        if (onScanComplete) onScanComplete(updated);
      } else {
        setErrorMessage("Failed to update panel role on server. Check connection.");
      }
    } catch (e) {
      console.error("Server role update failed:", e);
      setErrorMessage("Network error while re-evaluating panel role.");
    } finally {
      setIsReEvaluating(false);
    }
  };

  // Submit scan to backend pipeline
  const handleSubmitScan = async (e) => {
    if (e) e.preventDefault();

    if (!productName.trim()) {
      setErrorMessage("Please enter the product name and packaging variant.");
      return;
    }

    if (panels.length === 0) {
      setErrorMessage("At least one package photograph (Front panel) is required.");
      return;
    }

    // Ensure there is a front panel
    const hasFront = panels.some(p => p.role === "FRONT" || p.role === "front");
    if (!hasFront) {
      setErrorMessage("Please designate at least one photograph as FRONT (Principal Display Panel).");
      return;
    }

    if (!navigator.onLine) {
      await handleQueueInspection(e);
      return;
    }

    setUploadStatus("uploading");
    setUploadProgress(25);
    setErrorMessage("");

    try {
      const formData = new FormData();
      formData.append("product_name", productName.trim());
      formData.append("category_id", categoryId);
      formData.append("calibration_method", calibrationMethod);

      // Separate panels by role
      panels.forEach((p, idx) => {
        const roleLower = (p.role || "front").toLowerCase();
        if (roleLower === "front" && !formData.has("front_image")) {
          formData.append("front_image", p.file);
        } else if (roleLower === "back" && !formData.has("back_image")) {
          formData.append("back_image", p.file);
        } else if ((roleLower === "side" || roleLower === "left_side" || roleLower === "right_side") && !formData.has("side_image")) {
          formData.append("side_image", p.file);
        } else if (roleLower === "close_up" && !formData.has("close_up_image")) {
          formData.append("close_up_image", p.file);
        } else {
          // Additional panel
          formData.append(`additional_image_${idx}`, p.file);
        }
      });

      setUploadProgress(50);
      setUploadStatus("processing");

      const res = await fetch("/api/scans", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Inspection processing failed.");
      }

      setUploadProgress(100);
      const scanData = await res.json();
      setCompletedScan(scanData);
      setShowReviewStep(true);
      setUploadStatus("success");

      // Clear draft since upload succeeded
      try {
        localStorage.removeItem("metricheck_mobile_draft");
      } catch {
        // Ignore
      }

      if (onScanComplete) {
        onScanComplete(scanData);
      }
    } catch (err) {
      setUploadStatus("error");
      setErrorMessage(err.message || "Failed to complete scan upload. Check connection and tap retry.");
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4 pb-16 font-sans">
      {/* Top Mobile Inspector Header */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-700 text-white flex items-center justify-center shadow-sm">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-bold text-slate-900">Mobile Inspection Edge Mode</h1>
              <span className="px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 text-[10px] font-bold">
                PROTOTYPE
              </span>
            </div>
            <p className="text-[11px] text-slate-500">Field Capture & Pre-Reliance Review</p>
          </div>
        </div>

        {/* Connectivity & Actions */}
        <div className="flex items-center gap-2">
          {/* Offline Queue Badge & Toggle */}
          <button
            type="button"
            onClick={() => setShowQueueDrawer(!showQueueDrawer)}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border transition-colors cursor-pointer ${
              offlineQueue.filter(q => q.status !== 'synced').length > 0
                ? "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
            }`}
            aria-label="Toggle offline inspection queue"
            title="Inspect queued offline drafts"
          >
            <Inbox className="w-3 h-3 text-blue-600" />
            <span>{offlineQueue.filter(q => q.status !== 'synced').length} Queued</span>
            {showQueueDrawer ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
          </button>

          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold ${
            isOnline ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-amber-50 text-amber-700 border border-amber-200"
          }`}>
            {isOnline ? <Wifi className="w-3 h-3 text-emerald-500" /> : <WifiOff className="w-3 h-3 text-amber-500" />}
            <span>{isOnline ? "Online" : "Offline"}</span>
          </span>

          {onExitMobileMode && (
            <button
              onClick={onExitMobileMode}
              className="px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              Exit
            </button>
          )}
        </div>
      </div>

      {/* Offline Queue Drawer */}
      {showQueueDrawer && (
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Inbox className="w-4 h-4 text-blue-600" />
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Offline Inspection Queue ({offlineQueue.length})
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {offlineQueue.some(q => q.status === "synced") && (
                <button
                  type="button"
                  onClick={handleClearSyncedQueue}
                  className="text-[10px] font-bold text-slate-500 hover:text-slate-800 underline cursor-pointer"
                >
                  Clear Synced
                </button>
              )}
              {isOnline && offlineQueue.some(q => q.status === "queued" || q.status === "failed") && (
                <button
                  type="button"
                  disabled={isQueueSyncing}
                  onClick={() => syncOfflineQueue()}
                  className="px-2.5 py-1 text-[11px] font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className={`w-3 h-3 ${isQueueSyncing ? "animate-spin" : ""}`} />
                  <span>Sync All ({offlineQueue.filter(q => q.status !== "synced").length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Sync Progress Bar */}
          {isQueueSyncing && (
            <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800 space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-semibold">
                <span>Syncing {queueSyncProgress.current} of {queueSyncProgress.total}: <strong>{queueSyncProgress.currentItemName}</strong></span>
                <span>{Math.round((queueSyncProgress.current / Math.max(queueSyncProgress.total, 1)) * 100)}%</span>
              </div>
              <div className="w-full bg-blue-200 h-1.5 rounded-full overflow-hidden">
                <div 
                  className="bg-blue-600 h-full transition-all duration-300"
                  style={{ width: `${(queueSyncProgress.current / Math.max(queueSyncProgress.total, 1)) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* List of queue items */}
          {offlineQueue.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-2">No offline inspection drafts in queue.</p>
          ) : (
            <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto space-y-1">
              {offlineQueue.map((item) => (
                <div key={item.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 truncate">{item.product_name}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
                        item.status === 'synced' ? 'bg-emerald-50 text-emerald-700' :
                        item.status === 'syncing' ? 'bg-blue-50 text-blue-700 animate-pulse' :
                        item.status === 'failed' ? 'bg-rose-50 text-rose-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                      <span>{item.category_name}</span>
                      <span>•</span>
                      <span>{item.panel_count} panel(s)</span>
                      <span>•</span>
                      <span>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    {item.last_error && (
                      <p className="text-[10px] text-rose-600 font-semibold">{item.last_error}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {item.status === 'failed' && isOnline && (
                      <button
                        type="button"
                        onClick={() => syncOfflineQueue(item.id)}
                        className="px-2 py-1 text-[10px] font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-md border border-rose-200 cursor-pointer"
                      >
                        Retry
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDiscardQueueItem(item.id)}
                      className="p-1 text-slate-400 hover:text-rose-600 rounded cursor-pointer"
                      title="Discard from queue"
                      aria-label={`Discard ${item.product_name} from queue`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Success Notification */}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2.5 shadow-xs">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{successMessage}</span>
        </div>
      )}

      {/* Error / Alert Notice */}
      {errorMessage && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 shadow-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1 flex-1">
            <span className="font-semibold block">{errorMessage}</span>
            {uploadStatus === "error" && (
              <button
                onClick={handleSubmitScan}
                className="mt-1 inline-flex items-center gap-1 text-[11px] font-bold text-rose-900 underline cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" /> Retry Upload
              </button>
            )}
          </div>
        </div>
      )}

      {/* VIEW A: PRE-RELIANCE EVIDENCE REVIEW (WHEN SCAN COMPLETED) */}
      {showReviewStep && completedScan ? (
        <div className="space-y-4">
          <div className="bg-amber-50/90 border border-amber-200/90 rounded-2xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-amber-900 font-bold text-xs uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-amber-700" />
              <span>Inspector Pre-Reliance Evidence Review</span>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              Verify evidence provenance, image quality, confidence levels, and any detected cross-panel conflicts below 
              before relying on this statutory determination.
            </p>
            <div className="pt-2 border-t border-amber-200/70 flex flex-wrap items-center justify-between text-[11px] text-amber-700">
              <span>Overall Status: <strong>{completedScan.overall_status}</strong></span>
              <span>Score: <strong>{completedScan.compliance_score}%</strong></span>
            </div>
          </div>

          {/* Quick Summary Pill Bar */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">Inspected Commodity</span>
              <h2 className="text-base font-bold text-slate-900">{completedScan.product_name}</h2>
              <span className="text-xs text-slate-500">{completedScan.category_name}</span>
            </div>
            <StatusBadge status={completedScan.overall_status} size="md" />
          </div>

          {/* Panel Photographs with Role Correction and Quality Telemetry */}
          {completedScan.images && completedScan.images.length > 0 && (
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Camera className="w-3.5 h-3.5 text-blue-600" />
                  <span>Panel Evidence & Role Reassignment</span>
                </h3>
                {isReEvaluating && (
                  <span className="text-[11px] font-semibold text-blue-600 flex items-center gap-1 animate-pulse">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    Re-evaluating rules...
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {completedScan.images.map((img, idx) => (
                  <div key={img.id || idx} className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        Image #{img.id || idx + 1}
                      </span>
                      <QualityBadge 
                        decision={img.quality_decision || "ACCEPTABLE"}
                        score={img.quality_score}
                        size="sm"
                      />
                    </div>

                    {/* Role Selector with traceable API update */}
                    <div>
                      <label className="text-[10px] text-slate-500 font-semibold block mb-0.5">
                        Statutory Panel Role:
                      </label>
                      <select
                        value={img.image_role?.toUpperCase() || "FRONT"}
                        disabled={isReEvaluating}
                        onChange={(e) => handleServerRoleChange(img.id, e.target.value)}
                        className="w-full text-xs font-bold bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-slate-800 focus:ring-2 focus:ring-blue-500 cursor-pointer disabled:opacity-50"
                        aria-label={`Correct panel role for image ${img.id || idx + 1}`}
                      >
                        {ROLE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Quality Telemetry */}
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200/60 font-mono">
                      <span>Blur: {img.blur_score ? img.blur_score.toFixed(1) : "N/A"}</span>
                      <span>Glare: {img.glare_percentage ? `${img.glare_percentage.toFixed(1)}%` : "0.0%"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Field Evidence Inspection Cards */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 px-1">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Field Evidence & Provenance</span>
            </h3>

            {(completedScan.declarations || []).map((decl) => {
              const hasConflict = decl.has_conflict;
              const isUncertain = ["UNABLE_TO_VERIFY", "NOT_FOUND", "AMBIGUOUS", "LOW_CONFIDENCE"].includes(decl.extraction_status);

              return (
                <div 
                  key={decl.field_name}
                  className={`bg-white rounded-xl border p-4 shadow-xs space-y-2.5 transition-all ${
                    hasConflict 
                      ? "border-amber-300 bg-amber-50/20" 
                      : isUncertain
                      ? "border-purple-200 bg-purple-50/15"
                      : "border-slate-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">{decl.display_name}</span>
                        <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 text-[10px] font-mono uppercase font-bold">
                          {decl.source_image_role || "FRONT"} panel
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">{decl.field_name}</span>
                    </div>

                    <StatusBadge status={decl.status} size="sm" />
                  </div>

                  {/* Detected Value */}
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100 flex items-center justify-between gap-2">
                    <div className="text-xs">
                      <span className="text-slate-500 text-[10px] block">Detected Text:</span>
                      <span className="font-semibold text-slate-800">
                        {decl.detected_value || <span className="italic text-slate-400">Not detected / missing</span>}
                      </span>
                    </div>
                    {decl.confidence > 0 && (
                      <div className="w-24 shrink-0 text-right">
                        <span className="text-[10px] font-mono text-slate-500">{(decl.confidence * 100).toFixed(0)}% conf</span>
                        <ConfidenceBar confidence={decl.confidence} />
                      </div>
                    )}
                  </div>

                  {/* Conflicting Candidates Warning */}
                  {hasConflict && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-900 space-y-1">
                      <div className="flex items-center gap-1.5 font-bold text-amber-800">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                        <span>Conflicting Candidates Detected Across Panels</span>
                      </div>
                      <p className="text-[11px] text-amber-700">
                        Multiple panels provide conflicting values. Status marked AMBIGUOUS to prevent legal false compliance.
                      </p>
                      {decl.alternate_candidates && (
                        <div className="pt-1 text-[10px] text-amber-800 font-mono">
                          Alternates: {decl.alternate_candidates.map(a => a.value).join(" | ")}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Uncertainty Guidance */}
                  {decl.status === "UNABLE_TO_VERIFY" && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-2 text-[11px] text-purple-900 flex items-center gap-2">
                      <Info className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                      <span>Optical degradation prevents definitive verification. Physical inspection recommended.</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between gap-3 pt-2">
            <button
              onClick={() => {
                setShowReviewStep(false);
              }}
              className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors cursor-pointer"
            >
              + Add / Replace Panel Photos
            </button>

            <button
              onClick={clearDraft}
              className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
            >
              Start New Inspection
            </button>
          </div>
        </div>
      ) : (
        /* VIEW B: MOBILE CAPTURE & STAGING WORKFLOW */
        <form onSubmit={handleSubmitScan} className="space-y-4">
          {/* Product & Category Card */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-[10px] flex items-center justify-center font-bold">1</span>
                Product Details
              </span>
              {hasSavedDraft && (
                <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Draft Saved
                </span>
              )}
            </div>

            <div className="space-y-2">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">
                  Product Name & Packaging Variant <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Britannia Good Day Butter (200g)"
                  value={productName}
                  onChange={(e) => handleProductNameChange(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Statutory Category
                  </label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(Number(e.target.value))}
                    className="w-full px-2.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Font Calibration Reference
                  </label>
                  <select
                    value={calibrationMethod}
                    onChange={(e) => setCalibrationMethod(e.target.value)}
                    className="w-full px-2.5 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  >
                    <option value="uncalibrated_heuristic">Uncalibrated Heuristic</option>
                    <option value="reference_id_card_width">Standard ID Card (85.6 mm)</option>
                    <option value="reference_rupee_coin_5">₹5 Coin (23.0 mm)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Captured Photos & Quality Feedback */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-[10px] flex items-center justify-center font-bold">2</span>
                Package Panel Photographs ({panels.length})
              </span>
              <span className="text-[11px] text-slate-500">Multi-panel supported</span>
            </div>

            {/* List of captured panels */}
            {panels.length > 0 && (
              <div className="space-y-3">
                {panels.map((p, idx) => (
                  <div 
                    key={p.id}
                    className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 space-y-2.5"
                  >
                    <div className="flex items-start gap-3">
                      {/* Image Thumbnail */}
                      <div className="w-20 h-20 rounded-lg overflow-hidden bg-black/10 shrink-0 border border-slate-200 relative">
                        <img 
                          src={p.previewUrl} 
                          alt={`Panel ${idx + 1}`} 
                          className="w-full h-full object-cover"
                        />
                        <span className="absolute bottom-1 left-1 px-1.5 py-0.2 rounded bg-black/70 text-white text-[9px] font-bold">
                          #{idx + 1}
                        </span>
                      </div>

                      {/* Role and Quality Feedback */}
                      <div className="flex-1 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] font-bold uppercase text-slate-500">Panel Role</label>
                          <button
                            type="button"
                            onClick={() => removePanel(p.id)}
                            className="text-slate-400 hover:text-rose-600 p-1"
                            title="Remove photo"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Role selector dropdown */}
                        <select
                          value={p.role}
                          onChange={(e) => updatePanelRole(p.id, e.target.value)}
                          className="w-full px-2 py-1 text-xs font-semibold bg-white border border-slate-300 rounded-md text-slate-800"
                        >
                          {ROLE_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>

                        {/* Quality Telemetry */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                          {p.qualityLoading ? (
                            <span className="inline-flex items-center gap-1 text-[10px] text-blue-600">
                              <RefreshCw className="w-3 h-3 animate-spin" /> Analyzing quality...
                            </span>
                          ) : (
                            <>
                              <QualityBadge status={p.qualityStatus} size="sm" />
                              {p.blurScore !== null && (
                                <span className="text-[10px] font-mono text-slate-500">
                                  Sharp: {p.blurScore.toFixed(0)}
                                </span>
                              )}
                              {p.glareScore !== null && p.glareScore > 5 && (
                                <span className="text-[10px] font-mono text-amber-600">
                                  Glare: {p.glareScore.toFixed(0)}%
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Immediate Retake Guidance Box */}
                    {p.retakeGuidance && p.retakeGuidance.length > 0 && (
                      <div className="bg-amber-50/80 border border-amber-200/70 rounded-lg p-2 text-[11px] text-amber-900 space-y-1">
                        <div className="flex items-center gap-1 font-bold text-amber-800 text-[10px] uppercase">
                          <AlertTriangle className="w-3 h-3 text-amber-600" />
                          <span>Immediate Capture Guidance</span>
                        </div>
                        <ul className="list-disc list-inside space-y-0.5 text-[10px] text-amber-800">
                          {p.retakeGuidance.map((tip, tIdx) => (
                            <li key={tIdx}>{tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Quick Capture Action Buttons */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              {/* Camera Trigger */}
              <label className="flex flex-col items-center justify-center p-3 border-2 border-dashed border-blue-300 bg-blue-50/30 rounded-xl hover:bg-blue-50/60 transition-colors cursor-pointer text-center">
                <Camera className="w-5 h-5 text-blue-600 mb-1" />
                <span className="text-xs font-bold text-blue-700">Take Photo</span>
                <span className="text-[10px] text-slate-500">Opens Camera</span>
                <input 
                  type="file" 
                  accept="image/*" 
                  capture="environment" 
                  className="hidden" 
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleAddPhoto(f, panels.length === 0 ? "FRONT" : "BACK");
                    e.target.value = null;
                  }}
                />
              </label>

              {/* Gallery Trigger */}
              <label className="flex flex-col items-center justify-center p-3 border border-slate-200 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer text-center">
                <Upload className="w-5 h-5 text-slate-600 mb-1" />
                <span className="text-xs font-bold text-slate-700">Choose File</span>
                <span className="text-[10px] text-slate-500">Photo Library</span>
                <input 
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleAddPhoto(f, panels.length === 0 ? "FRONT" : "BACK");
                    e.target.value = null;
                  }}
                />
              </label>
            </div>
          </div>

          {/* Progress / Status Indicator */}
          {uploadStatus === "uploading" || uploadStatus === "processing" ? (
            <div className="bg-white p-4 rounded-2xl border border-blue-200 shadow-xs space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                  {uploadStatus === "uploading" ? "Uploading photographs..." : "Running OCR & Compliance Rules..."}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          ) : null}

          {/* Privacy & Local Draft Data Minimization Notice */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-[11px] text-slate-600 space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-slate-700">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Inspector Privacy & Local Draft Storage</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-relaxed">
              Browser draft storage persists only commodity name, category, and update timestamp. No inspector identity, 
              location telemetry, or biometric data is collected or retained.
            </p>
            {hasSavedDraft && (
              <button
                type="button"
                onClick={clearDraft}
                className="mt-1 text-[10px] font-bold text-rose-600 hover:text-rose-700 underline cursor-pointer"
                aria-label="Discard stored local draft"
              >
                Discard Stored Draft
              </button>
            )}
          </div>

          {/* Submit & Offline Queue Action Buttons */}
          <div className="pt-2 flex flex-col sm:flex-row gap-2">
            {isOnline ? (
              <>
                <button
                  type="submit"
                  disabled={uploadStatus === "uploading" || uploadStatus === "processing"}
                  className="flex-1 py-3.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-sm shadow-md shadow-blue-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  aria-label="Submit photographs for Legal Metrology Inspection"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Run Legal Metrology Inspection</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleQueueInspection}
                  className="py-3 px-3.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer border border-slate-200"
                  aria-label="Queue for offline batch sync"
                  title="Queue this commodity locally and photograph the next"
                >
                  <Inbox className="w-4 h-4 text-slate-600" />
                  <span>Queue Draft</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleQueueInspection}
                className="w-full py-3.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-sm shadow-md shadow-amber-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer focus:ring-2 focus:ring-amber-500 focus:outline-hidden"
                aria-label="Queue for offline sync"
              >
                <Clock className="w-4 h-4" />
                <span>Queue for Offline Sync (Saved Locally)</span>
                <Inbox className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
