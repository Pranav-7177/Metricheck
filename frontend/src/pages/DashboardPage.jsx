import React, { useState } from 'react';
import { 
  ShieldCheck, AlertTriangle, HelpCircle, CheckCircle2, 
  ArrowRight, Search, Filter, RefreshCw, Calendar, Tag, Smartphone
} from 'lucide-react';
import StatusBadge from '../components/StatusBadge';

export default function DashboardPage({ stats, loading, onRefresh, onViewScan, onStartNewScan, onStartMobileInspection }) {
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  if (loading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-medium text-slate-600">Loading inspection dashboard metrics...</p>
      </div>
    );
  }

  const scans = stats?.recent_scans || [];
  const filteredScans = scans.filter(s => {
    const matchesStatus = filterStatus === "ALL" || s.overall_status === filterStatus;
    const matchesSearch = s.product_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (s.category_name && s.category_name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-6 sm:p-8 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-800/80 text-blue-200 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Inspection & Compliance Assistance System</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Legal Metrology Compliance Scanner
            </h1>
            <p className="text-sm text-blue-100 leading-relaxed">
              Automated packaging text extraction, statutory declaration verification (MRP, Net Qty, Dates, Mfg, Consumer Care), 
              physical font height estimation, and uncertainty-aware compliance reporting under Indian regulations.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 self-start md:self-center shrink-0">
            <button
              onClick={onStartNewScan}
              className="px-4 py-2.5 rounded-xl bg-white text-blue-900 hover:bg-blue-50 font-semibold text-xs sm:text-sm shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span>Scan Packaging</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {onStartMobileInspection && (
              <button
                onClick={onStartMobileInspection}
                className="px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs sm:text-sm shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <Smartphone className="w-4 h-4" />
                <span>Mobile Edge</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Uncertainty & Legal Assistance Explainer */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-900 flex items-start gap-3">
        <HelpCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-blue-950">
            Crucial Distinction: "Not Detected" vs. "Unable to Verify"
          </p>
          <p className="text-blue-800 leading-relaxed">
            MetriCheck handles uncertainty transparently. <strong>UNABLE TO VERIFY</strong> denotes degraded image quality, blur, glare, 
            or low OCR confidence—it is <em>never</em> automatically classified as a statutory violation. 
            <strong>POTENTIAL NON-COMPLIANCE</strong> indicates a confirmed rule discrepancy requiring inspector review.
          </p>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scans */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-medium uppercase tracking-wider">Total Scans</span>
            <Tag className="w-4 h-4 text-slate-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold text-slate-900 font-mono">
              {stats?.total_scans ?? 0}
            </span>
            <span className="text-xs text-slate-500">All categories</span>
          </div>
          <p className="text-xs text-slate-500">Packaged commodities logged</p>
        </div>

        {/* Verified Compliant */}
        <div className="bg-white p-5 rounded-xl border border-emerald-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-emerald-700">
            <span className="text-xs font-medium uppercase tracking-wider">Verified Compliant</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold text-emerald-700 font-mono">
              {stats?.verified_compliant ?? 0}
            </span>
            <span className="text-xs font-semibold text-emerald-600">
              {stats?.compliance_rate_percent ?? 0}% rate
            </span>
          </div>
          <p className="text-xs text-slate-500">All mandatory rules verified</p>
        </div>

        {/* Potential Issues */}
        <div className="bg-white p-5 rounded-xl border border-rose-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-rose-700">
            <span className="text-xs font-medium uppercase tracking-wider">Potential Issues</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold text-rose-700 font-mono">
              {stats?.potential_non_compliance ?? 0}
            </span>
            <span className="text-xs text-rose-600 font-medium">Notice candidate</span>
          </div>
          <p className="text-xs text-slate-500">Requires physical verification</p>
        </div>

        {/* Unable to Verify */}
        <div className="bg-white p-5 rounded-xl border border-amber-100 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-amber-700">
            <span className="text-xs font-medium uppercase tracking-wider">Unable to Verify</span>
            <HelpCircle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold text-amber-700 font-mono">
              {stats?.unable_to_verify ?? 0}
            </span>
            <span className="text-xs text-amber-600 font-medium">Needs re-scan</span>
          </div>
          <p className="text-xs text-slate-500">Blurry, glare, or occluded text</p>
        </div>
      </div>

      {/* Recent Scans Table Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Table Header Controls */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Recent Packaging Scans</h2>
            <p className="text-xs text-slate-500">Audit logs and compliance determinations</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search product..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>

            {/* Filter by Status */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-xs">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-transparent text-slate-700 font-medium focus:outline-hidden cursor-pointer"
              >
                <option value="ALL">All Statuses</option>
                <option value="VERIFIED_COMPLIANT">Verified Compliant</option>
                <option value="POTENTIAL_NON_COMPLIANCE">Potential Non-Compliance</option>
                <option value="UNABLE_TO_VERIFY">Unable to Verify</option>
                <option value="REVIEW_REQUIRED">Review Required</option>
              </select>
            </div>

            {/* Refresh */}
            <button
              onClick={onRefresh}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 cursor-pointer"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Table Content */}
        {filteredScans.length === 0 ? (
          <div className="p-8 text-center text-slate-500 space-y-3">
            <Search className="w-8 h-8 mx-auto text-slate-400" />
            <p className="text-sm font-medium">No packaging scans found matching the criteria.</p>
            <button
              onClick={onStartNewScan}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold cursor-pointer"
            >
              Start a new scan
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4">Product Name & Category</th>
                  <th className="py-3 px-4">Compliance Status</th>
                  <th className="py-3 px-4">Compliance Score</th>
                  <th className="py-3 px-4">Calibration</th>
                  <th className="py-3 px-4">Date Scanned</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredScans.map((scan) => (
                  <tr
                    key={scan.id}
                    className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                    onClick={() => onViewScan(scan.id)}
                  >
                    <td className="py-3.5 px-4 font-medium text-slate-900">
                      <div>
                        <span className="font-semibold text-sm group-hover:text-blue-700 transition-colors">
                          {scan.product_name}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-medium">
                            {scan.category_name || "General"}
                          </span>
                          {scan.is_demo && (
                            <span className="px-1.5 py-0.2 rounded-sm bg-purple-50 text-purple-700 border border-purple-200 text-[9px] font-bold">
                              DEMO
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <StatusBadge status={scan.overall_status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                          <div
                            className={`h-full rounded-full ${
                              scan.compliance_score >= 80 ? 'bg-emerald-500' :
                              scan.compliance_score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(5, scan.compliance_score))}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs font-medium text-slate-700">
                          {scan.compliance_score}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      {scan.is_calibrated ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                          Calibrated (mm verified)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
                          Heuristic estimate
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{new Date(scan.created_at).toLocaleDateString(undefined, {
                          month: 'short', day: 'numeric', year: 'numeric'
                        })}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewScan(scan.id);
                        }}
                        className="px-3 py-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors cursor-pointer"
                      >
                        Audit Report →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
