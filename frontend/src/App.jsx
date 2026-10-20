import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import NewScanPage from './pages/NewScanPage';
import AnalysisPage from './pages/AnalysisPage';
import ResultsPage from './pages/ResultsPage';
import RulesExplorerPage from './pages/RulesExplorerPage';
import MobileInspectionMode from './components/MobileInspectionMode';
import { Info } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, new_scan, analysis, results, rules, mobile
  const [stats, setStats] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Selected scan for viewing
  const [currentScan, setCurrentScan] = useState(null);
  const [inProgressScan, setInProgressScan] = useState(null);

  // Fetch initial dashboard metrics and categories
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [statsRes, catRes] = await Promise.all([
        fetch("/api/dashboard/stats"),
        fetch("/api/categories")
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (catRes.ok) {
        const catData = await catRes.json();
        setCategories(catData);
      }
    } catch (e) {
      console.error("Error connecting to backend API:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleScanCreated = (scanResult) => {
    setInProgressScan(scanResult);
    setActiveTab("analysis");
  };

  const handleAnalysisComplete = (completedScan) => {
    setCurrentScan(completedScan);
    setActiveTab("results");
    fetchInitialData(); // Refresh recent scans and counts
  };

  const handleViewScan = async (scanId) => {
    try {
      const res = await fetch(`/api/scans/${scanId}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentScan(data);
        setActiveTab("results");
      }
    } catch (e) {
      console.error("Failed to load scan details:", e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col selection:bg-blue-100 selection:text-blue-900">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={(tab) => {
          if (tab === "dashboard") {
            fetchInitialData();
          }
          setActiveTab(tab);
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeTab === "dashboard" && (
          <DashboardPage
            stats={stats}
            loading={loading}
            onRefresh={fetchInitialData}
            onViewScan={handleViewScan}
            onStartNewScan={() => setActiveTab("new_scan")}
            onStartMobileInspection={() => setActiveTab("mobile")}
          />
        )}

        {activeTab === "mobile" && (
          <MobileInspectionMode
            categories={categories}
            initialScan={currentScan}
            onScanComplete={(scanResult) => {
              setCurrentScan(scanResult);
              fetchInitialData();
            }}
            onExitMobileMode={() => {
              fetchInitialData();
              setActiveTab("dashboard");
            }}
          />
        )}

        {activeTab === "new_scan" && (
          <NewScanPage
            categories={categories}
            onScanCreated={handleScanCreated}
            onCancel={() => setActiveTab("dashboard")}
          />
        )}

        {activeTab === "analysis" && (
          <AnalysisPage
            scanResult={inProgressScan}
            onComplete={handleAnalysisComplete}
          />
        )}

        {activeTab === "results" && (
          <ResultsPage
            scan={currentScan}
            onBack={() => {
              fetchInitialData();
              setActiveTab("dashboard");
            }}
            onRefresh={() => handleViewScan(currentScan?.id)}
          />
        )}

        {activeTab === "rules" && (
          <RulesExplorerPage
            categories={categories}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-auto py-6 px-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="space-y-1 text-center sm:text-left">
            <p className="font-semibold text-slate-800">
              Legal Metrology Packaged Commodities Compliance Scanner (MetriCheck)
            </p>
            <p className="text-[11px] text-slate-400">
              Engineered for Hackathon Showcase • Standards based on Legal Metrology (Packaged Commodities) Rules, 2011
            </p>
          </div>

          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-[11px] text-slate-600 max-w-md">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700 mb-0.5">
              <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>Assistance & Prototype Disclaimer</span>
            </div>
            <span>
              This application is an explainable decision-support prototype. Final statutory determinations remain subject to authorized physical verification by Legal Metrology Officers.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
