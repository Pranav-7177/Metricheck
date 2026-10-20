import React from 'react';
import { ShieldCheck, PlusCircle, LayoutDashboard, BookOpen, AlertCircle, Smartphone } from 'lucide-react';

export default function Navbar({ activeTab, onTabChange }) {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
      {/* Top Advisory Strip */}
      <div className="bg-slate-900 text-slate-300 px-4 py-1.5 text-xs flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-medium text-white">MetriCheck Assistance System</span>
          <span className="hidden sm:inline text-slate-400">|</span>
          <span className="text-slate-400">Legal Metrology (Packaged Commodities) Rules, 2011</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>Prototype Assistant • Not a final legal determination</span>
        </div>
      </div>

      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={() => onTabChange("dashboard")}
          >
            <div className="w-10 h-10 rounded-xl bg-blue-700 text-white flex items-center justify-center shadow-md shadow-blue-500/20 group-hover:bg-blue-800 transition-colors">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-slate-900 font-sans">MetriCheck</span>
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 rounded-md">
                  v2024.1
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">Legal Metrology Packaged Commodities Scanner</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => onTabChange("dashboard")}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                activeTab === "dashboard"
                  ? "bg-blue-50 text-blue-700 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => onTabChange("mobile")}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                activeTab === "mobile"
                  ? "bg-purple-50 text-purple-700 font-bold border border-purple-200"
                  : "text-slate-600 hover:text-purple-700 hover:bg-purple-50/50"
              }`}
            >
              <Smartphone className="w-4 h-4 text-purple-600" />
              <span className="hidden xs:inline">Mobile Edge</span>
            </button>

            <button
              onClick={() => onTabChange("rules")}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer ${
                activeTab === "rules"
                  ? "bg-blue-50 text-blue-700 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span className="hidden sm:inline">Rules Explorer</span>
            </button>

            <button
              onClick={() => onTabChange("new_scan")}
              className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-semibold rounded-lg text-white bg-blue-600 hover:bg-blue-700 shadow-sm shadow-blue-500/25 transition-all cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Scan</span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}
