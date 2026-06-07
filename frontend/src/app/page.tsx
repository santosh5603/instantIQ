"use client";

import React, { useState, useEffect } from "react";
import { 
  LayoutDashboard, 
  Instagram, 
  FolderArchive, 
  Users, 
  Terminal, 
  Search, 
  RotateCw, 
  Plus, 
  ExternalLink, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Hourglass, 
  Notion, 
  Trash2, 
  Send, 
  HelpCircle,
  Database,
  RefreshCw,
  Sliders,
  PlayCircle
} from "lucide-react";

// Mock Fallback Data (used when backend is offline for visual demonstration resilience)
const MOCK_ANALYTICS = {
  overall_conversion: { total_reels: 14, completed_reels: 11, failed_reels: 2, conversion_rate: 78.57 },
  status_distribution: [
    { status: "completed", count: 11 },
    { status: "waiting_dm", count: 1 },
    { status: "failed", count: 2 }
  ],
  category_distribution: [
    { category: "AI", count: 5 },
    { category: "Programming", count: 3 },
    { category: "Career", count: 2 },
    { category: "Fitness", count: 1 }
  ],
  queue_metrics: { reels_queue_length: 0, notion_queue_length: 0, dlq_queue_length: 0 },
  total_resources: 11,
  total_creators_followed: 4
};

const MOCK_REELS = [
  {
    id: "a1a8c91d-e6b9-4785-bb90-b9627702f232",
    reel_url: "https://www.instagram.com/reel/C5_t9u2RxgY/",
    creator_name: "tech_guide_ai",
    caption: "Comment GUIDE to get my ultimate 100+ AI Tools Toolkit free! Must follow to receive the automated download package.",
    requires_comment: true,
    requires_follow: true,
    comment_keyword: "GUIDE",
    commented: true,
    followed: true,
    status: "completed",
    processed_at: "2026-05-22T17:15:00Z",
    created_at: "2026-05-22T17:10:00Z"
  },
  {
    id: "b2b8c91d-e6b9-4785-bb90-b9627702f233",
    reel_url: "https://www.instagram.com/reel/C6_code123/",
    creator_name: "javascript_master",
    caption: "Write CODE below and I will DM you my master JS cheat sheet. Follow me for more advanced coding algorithms.",
    requires_comment: true,
    requires_follow: true,
    comment_keyword: "CODE",
    commented: true,
    followed: true,
    status: "waiting_dm",
    processed_at: null,
    created_at: "2026-05-22T17:55:00Z"
  },
  {
    id: "c3c8c91d-e6b9-4785-bb90-b9627702f234",
    reel_url: "https://www.instagram.com/reel/C7_fail999/",
    creator_name: "marketing_guru",
    caption: "Comment PDF to access our organic growth masterclass toolkit.",
    requires_comment: true,
    requires_follow: false,
    comment_keyword: "PDF",
    commented: false,
    followed: false,
    status: "failed",
    error_message: "Network Timeout: Instagram rate-limited commenting action.",
    processed_at: null,
    created_at: "2026-05-22T16:00:00Z"
  }
];

const MOCK_RESOURCES = [
  {
    id: "r1a8c91d-e6b9-4785-bb90-b9627702f235",
    reel_id: "a1a8c91d-e6b9-4785-bb90-b9627702f232",
    resource_type: "pdf",
    resource_url: "https://drive.google.com/file/d/1ai_tools_toolkit/view",
    resource_text: "Ultimate 100+ AI Tools Toolkit.pdf",
    category: "AI",
    notion_synced: true,
    notion_page_id: "page-12345",
    received_at: "2026-05-22T17:15:00Z"
  },
  {
    id: "r2b8c91d-e6b9-4785-bb90-b9627702f236",
    reel_id: "a1a8c91d-e6b9-4785-bb90-b9627702f232",
    resource_type: "link",
    resource_url: "https://github.com/ai-builders/tooling",
    resource_text: "GitHub - AI Builder Resources",
    category: "Programming",
    notion_synced: true,
    notion_page_id: "page-12346",
    received_at: "2026-05-22T17:15:00Z"
  }
];

const MOCK_CREATORS = [
  { id: "cr1", creator_name: "tech_guide_ai", followed: true, followed_at: "2026-05-22T17:11:00Z", total_reels: 3, total_resources: 2 },
  { id: "cr2", creator_name: "javascript_master", followed: true, followed_at: "2026-05-22T17:56:00Z", total_reels: 1, total_resources: 0 }
];

const MOCK_LOGS = [
  { id: "l1", step_name: "discovery", status: "success", message: "Discovered Reel URL from inbox direct messages.", timestamp: "2026-05-22T17:10:05Z" },
  { id: "l2", step_name: "extraction", status: "success", message: "Extracted caption & creator @tech_guide_ai.", timestamp: "2026-05-22T17:11:00Z" },
  { id: "l3", step_name: "follow_automation", status: "success", message: "Successfully followed creator @tech_guide_ai.", timestamp: "2026-05-22T17:11:45Z" },
  { id: "l4", step_name: "comment_automation", status: "success", message: "Posted comment keyword 'GUIDE'.", timestamp: "2026-05-22T17:12:30Z" },
  { id: "l5", step_name: "dm_harvest", status: "success", message: "Harvested 2 links from DM responses.", timestamp: "2026-05-22T17:15:00Z" },
  { id: "l6", step_name: "notion_sync", status: "success", message: "Synced DMResource items directly to Notion database.", timestamp: "2026-05-22T17:15:15Z" }
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [backendOnline, setBackendOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // App States
  const [analytics, setAnalytics] = useState(MOCK_ANALYTICS);
  const [reels, setReels] = useState(MOCK_REELS);
  const [resources, setResources] = useState(MOCK_RESOURCES);
  const [creators, setCreators] = useState(MOCK_CREATORS);
  const [logs, setLogs] = useState(MOCK_LOGS);
  
  // Form State
  const [reelUrlInput, setReelUrlInput] = useState("");
  const [creatorInput, setCreatorInput] = useState("");
  const [formStatus, setFormStatus] = useState<{ type: "success" | "error" | null; msg: string }>({ type: null, msg: "" });
  
  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchActive, setSearchActive] = useState(false);

  const API_BASE = "http://localhost:8000";

  // Fetch all states from local FastAPI Backend if online
  const refreshData = async () => {
    setLoading(true);
    try {
      // 1. Health check
      const healthRes = await fetch(`${API_BASE}/health`);
      if (healthRes.ok) {
        setBackendOnline(true);
        
        // Load actual data
        const analyticsRes = await fetch(`${API_BASE}/analytics`);
        if (analyticsRes.ok) setAnalytics(await analyticsRes.json());

        const reelsRes = await fetch(`${API_BASE}/reels?per_page=50`);
        if (reelsRes.ok) {
          const res = await reelsRes.json();
          setReels(res.data);
        }

        const resourcesRes = await fetch(`${API_BASE}/resources?per_page=50`);
        if (resourcesRes.ok) {
          const res = await resourcesRes.json();
          setResources(res.data);
        }

        const creatorsRes = await fetch(`${API_BASE}/creators?per_page=50`);
        if (creatorsRes.ok) {
          const res = await creatorsRes.json();
          setCreators(res.data);
        }

        const logsRes = await fetch(`${API_BASE}/logs?per_page=50`);
        if (logsRes.ok) {
          const res = await logsRes.json();
          setLogs(res.data);
        }
      } else {
        setBackendOnline(false);
      }
    } catch (e) {
      console.warn("Backend server seems offline. Operating in visual demo mode.");
      setBackendOnline(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
    // Auto refresh every 20 seconds
    const interval = setInterval(refreshData, 20000);
    return () => clearInterval(interval);
  }, []);

  // Form submission
  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reelUrlInput || !reelUrlInput.includes("instagram.com")) {
      setFormStatus({ type: "error", msg: "Please enter a valid Instagram Reel URL." });
      return;
    }

    setFormStatus({ type: "success", msg: "Sending to worker queue..." });

    if (backendOnline) {
      try {
        const res = await fetch(`${API_BASE}/reels`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reel_url: reelUrlInput.trim(),
            creator_name: creatorInput.trim() || null
          })
        });

        if (res.status === 201) {
          setFormStatus({ type: "success", msg: "Reel successfully queued! Background Playwright worker dispatched." });
          setReelUrlInput("");
          setCreatorInput("");
          refreshData();
        } else {
          const err = await res.json();
          setFormStatus({ type: "error", msg: err.detail || "Submission failed." });
        }
      } catch (e) {
        setFormStatus({ type: "error", msg: "Failed to communicate with API server." });
      }
    } else {
      // Mock flow locally for immediate UI response
      const newMockReel = {
        id: `mock-${uuid()}`,
        reel_url: reelUrlInput.trim(),
        creator_name: creatorInput.trim() || "extracted_creator",
        caption: "Comment GUIDE below to fetch resources.",
        requires_comment: true,
        requires_follow: false,
        comment_keyword: "GUIDE",
        commented: false,
        followed: false,
        status: "pending",
        created_at: new Date().toISOString()
      };
      setReels([newMockReel, ...reels]);
      setFormStatus({ type: "success", msg: "[Demo Mode] Added reel in pending state to local dashboard list." });
      setReelUrlInput("");
      setCreatorInput("");
    }
  };

  // Search Action
  const triggerSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchActive(false);
      return;
    }

    if (backendOnline) {
      try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(searchQuery)}`);
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.data);
          setSearchActive(true);
        }
      } catch (e) {
        logger.error("FTS search query failed.");
      }
    } else {
      // Local Mock Filter
      const matched = resources.filter(res => 
        res.file_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        res.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        res.resource_url.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setSearchResults(matched);
      setSearchActive(true);
    }
  };

  // Manual actions
  const triggerRetry = async (reelId: string) => {
    if (backendOnline) {
      try {
        await fetch(`${API_BASE}/reels/${reelId}/retry`, { method: "POST" });
        refreshData();
      } catch (e) {
        console.error(e);
      }
    } else {
      // Visual mock change
      setReels(reels.map(r => r.id === reelId ? { ...r, status: "pending", error_message: null } : r));
    }
  };

  const triggerNotionSync = async (resourceId: string) => {
    if (backendOnline) {
      try {
        await fetch(`${API_BASE}/resources/${resourceId}/sync`, { method: "POST" });
        refreshData();
      } catch (e) {
        console.error(e);
      }
    } else {
      // Visual mock change
      setResources(resources.map(res => res.id === resourceId ? { ...res, notion_synced: true, notion_page_id: "notion-synced-12" } : res));
    }
  };

  function uuid() {
    return Math.random().toString(36).substring(2, 9);
  }

  // Get status color tag
  const getStatusBadge = (status: string) => {
    const map: Record<string, { bg: string, text: string, icon: any }> = {
      pending: { bg: "bg-slate-500/10 border-slate-500/30", text: "text-slate-400", icon: Hourglass },
      extracting_caption: { bg: "bg-cyan-500/10 border-cyan-500/30", text: "text-cyan-400", icon: RotateCw },
      cta_detected: { bg: "bg-violet-500/10 border-violet-500/30", text: "text-violet-400", icon: AlertCircle },
      no_cta: { bg: "bg-amber-500/10 border-amber-500/30", text: "text-amber-400", icon: AlertCircle },
      awaiting_follow: { bg: "bg-indigo-500/10 border-indigo-500/30", text: "text-indigo-400", icon: Hourglass },
      following: { bg: "bg-emerald-500/10 border-emerald-500/30", text: "text-emerald-400", icon: CheckCircle2 },
      awaiting_comment: { bg: "bg-blue-500/10 border-blue-500/30", text: "text-blue-400", icon: Hourglass },
      commenting: { bg: "bg-blue-600/10 border-blue-600/30", text: "text-blue-300", icon: RotateCw },
      commented: { bg: "bg-sky-500/10 border-sky-500/30", text: "text-sky-400", icon: CheckCircle2 },
      waiting_dm: { bg: "bg-purple-500/10 border-purple-500/30", text: "text-purple-400 font-semibold animate-pulse", icon: Send },
      dm_received: { bg: "bg-emerald-500/10 border-emerald-500/30", text: "text-emerald-400", icon: CheckCircle2 },
      completed: { bg: "bg-emerald-500/15 border-emerald-500/40", text: "text-emerald-300 font-medium", icon: CheckCircle2 },
      failed: { bg: "bg-rose-500/10 border-rose-500/30", text: "text-rose-400", icon: AlertCircle },
      dm_timeout: { bg: "bg-yellow-500/10 border-yellow-500/30", text: "text-yellow-400", icon: AlertCircle }
    };
    
    const config = map[status] || { bg: "bg-gray-500/10 border-gray-500/30", text: "text-gray-400", icon: HelpCircle };
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border ${config.bg} ${config.text}`}>
        <Icon className="w-3.5 h-3.5" />
        {status.toUpperCase().replace("_", " ")}
      </span>
    );
  };

  return (
    <div className="flex min-h-screen bg-[#050608] text-slate-100">
      
      {/* SIDEBAR */}
      <aside className="w-72 border-r border-slate-800 bg-[#08090d]/80 backdrop-blur-xl flex flex-col justify-between p-6">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 mb-10 mt-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-violet-600 to-blue-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Instagram className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-extrabold text-xl tracking-tight text-white leading-none">REELISE</h1>
              <span className="text-[10px] uppercase font-bold text-violet-400/80 tracking-widest mt-1 block">Collector Engine</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {[
              { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
              { id: "reels", label: "Pipeline Reels", icon: Instagram },
              { id: "resources", label: "Harvested Second Brain", icon: FolderArchive },
              { id: "creators", label: "Tracked Creators", icon: Users },
              { id: "logs", label: "System Audit Logs", icon: Terminal }
            ].map(item => {
              const Icon = item.icon;
              const isSelected = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  id={`nav-btn-${item.id}`}
                  onClick={() => { setActiveTab(item.id); setSearchActive(false); }}
                  className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isSelected 
                      ? "bg-violet-600/10 text-violet-400 border border-violet-500/20" 
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isSelected ? "text-violet-400" : "text-slate-400"}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Info / Backend Status */}
        <div className="border-t border-slate-800 pt-6 mt-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs text-slate-400">Collector Connection</span>
            <div className="flex items-center gap-1.5">
              <div className={`w-2.5 h-2.5 rounded-full ${backendOnline ? "bg-emerald-500" : "bg-rose-500"}`} />
              <span className="text-xs font-semibold">{backendOnline ? "ONLINE" : "OFFLINE"}</span>
            </div>
          </div>
          
          <button 
            id="btn-refresh-dashboard"
            onClick={refreshData}
            className="w-full py-2.5 border border-slate-800 rounded-xl text-xs hover:bg-slate-800/40 hover:text-white transition-all flex items-center justify-center gap-2 text-slate-400"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Force Refresh
          </button>
        </div>
      </aside>

      {/* MAIN CONTAINER */}
      <main className="flex-1 flex flex-col max-h-screen overflow-y-auto">
        
        {/* TOP BAR HEADER */}
        <header className="border-b border-slate-800/80 bg-[#06070a]/90 backdrop-blur-xl px-10 py-5 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-4">
            <h2 className="text-2xl font-bold text-white tracking-tight capitalize">
              {activeTab === "dashboard" ? "System Command" : activeTab.replace("_", " ")}
            </h2>
            {loading && <span className="text-xs bg-slate-800 px-2.5 py-1 rounded text-slate-400 animate-pulse">refreshing...</span>}
          </div>

          <div className="flex items-center gap-4">
            {/* Queue depths ticker */}
            <div className="flex items-center gap-5 bg-slate-900/50 border border-slate-800 rounded-xl px-4 py-2 text-xs">
              <div className="flex items-center gap-2">
                <Database className="w-3.5 h-3.5 text-violet-400" />
                <span className="text-slate-400">Reel Queue:</span>
                <span className="font-bold text-violet-400">{analytics.queue_metrics.reels_queue_length}</span>
              </div>
              <div className="h-4 w-[1px] bg-slate-800" />
              <div className="flex items-center gap-2">
                <Notion className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-slate-400">Sync Queue:</span>
                <span className="font-bold text-blue-400">{analytics.queue_metrics.notion_queue_length}</span>
              </div>
              {analytics.queue_metrics.dlq_queue_length > 0 && (
                <>
                  <div className="h-4 w-[1px] bg-slate-800" />
                  <div className="flex items-center gap-2">
                    <span className="text-rose-400 font-medium">DLQ:</span>
                    <span className="font-bold text-rose-500 bg-rose-500/10 px-1.5 py-0.5 rounded">{analytics.queue_metrics.dlq_queue_length}</span>
                  </div>
                </>
              )}
            </div>

            {/* Notion Synced status badge */}
            <a
              href={`https://notion.so/`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4.5 py-2.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs text-white rounded-xl transition font-medium"
            >
              <Notion className="w-4 h-4 text-white" />
              Open Notion Dashboard
            </a>
          </div>
        </header>

        {/* WORKSPACE */}
        <div className="px-10 py-8 flex-1 space-y-8">
          
          {/* SEARCH BAR (Visible in all tabs) */}
          <form onSubmit={triggerSearch} className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-4.5 top-3.5 text-slate-500 w-4.5 h-4.5" />
              <input
                id="search-main-input"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search across extracted descriptions, keywords, files, or categories (AI, Code, Fitness)..."
                className="w-full bg-[#08090d] border border-slate-800 rounded-xl pl-12 pr-4 py-3.5 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500/60 transition"
              />
            </div>
            <button
              id="btn-trigger-search"
              type="submit"
              className="px-6 py-3.5 bg-gradient-to-r from-violet-600 to-blue-500 hover:from-violet-700 hover:to-blue-600 text-white rounded-xl text-sm font-semibold transition"
            >
              Search Hub
            </button>
          </form>

          {/* SEARCH RESULTS PANEL */}
          {searchActive && (
            <div className="glass-card p-6 border-violet-500/25">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-lg text-white flex items-center gap-2">
                  <Search className="w-5 h-5 text-violet-400" />
                  Search Results for "{searchQuery}" ({searchResults.length})
                </h3>
                <button 
                  onClick={() => { setSearchActive(false); setSearchQuery(""); }}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Clear Results
                </button>
              </div>

              {searchResults.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">
                  No matching files or reel resources discovered.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {searchResults.map(res => (
                    <div key={res.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold text-violet-400 tracking-wider uppercase bg-violet-500/10 px-2.5 py-0.5 rounded-full">{res.category}</span>
                          <span className="text-[10px] text-slate-500">{new Date(res.received_at).toLocaleDateString()}</span>
                        </div>
                        <h4 className="font-semibold text-slate-200 mb-1 text-sm line-clamp-1">{res.file_name}</h4>
                        <p className="text-xs text-slate-400 line-clamp-2">{res.resource_text}</p>
                      </div>

                      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-800/80">
                        <a 
                          href={res.resource_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex-1 py-2 text-center text-xs bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-all flex items-center justify-center gap-1.5"
                        >
                          <ExternalLink className="w-3.5 h-3.5" /> Direct Link
                        </a>
                        {res.notion_synced ? (
                          <span className="px-3 py-2 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Synced
                          </span>
                        ) : (
                          <button
                            onClick={() => triggerNotionSync(res.id)}
                            className="px-3 py-2 text-xs bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/20 rounded-lg transition"
                          >
                            Sync Notion
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* MAIN TAB SWITCHBOARD */}
          
          {/* TAB 1: GENERAL DASHBOARD */}
          {activeTab === "dashboard" && !searchActive && (
            <div className="space-y-8 animate-fade-in">
              
              {/* Analytics Metrics Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                {/* Total Reels */}
                <div className="glass-card p-6 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition">
                    <Instagram className="w-24 h-24 text-white" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block mb-1">Total Reels Forwarded</span>
                  <span className="text-4xl font-extrabold text-white block mt-2">{analytics.overall_conversion.total_reels}</span>
                  <div className="flex items-center gap-1 mt-3">
                    <span className="text-xs text-slate-400">Discovered from IG DM Inbox</span>
                  </div>
                </div>

                {/* Second Brain Resources */}
                <div className="glass-card p-6 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition">
                    <FolderArchive className="w-24 h-24 text-white" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block mb-1">Harvested PDF & Links</span>
                  <span className="text-4xl font-extrabold text-blue-400 block mt-2">{analytics.total_resources}</span>
                  <div className="flex items-center gap-1 mt-3">
                    <span className="text-xs text-slate-400">Uploaded to Supabase Storage</span>
                  </div>
                </div>

                {/* Creators followed */}
                <div className="glass-card p-6 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition">
                    <Users className="w-24 h-24 text-white" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block mb-1">Followed Creators</span>
                  <span className="text-4xl font-extrabold text-emerald-400 block mt-2">{analytics.total_creators_followed}</span>
                  <div className="flex items-center gap-1 mt-3">
                    <span className="text-xs text-slate-400">Active relationships tracked</span>
                  </div>
                </div>

                {/* Sync Rate */}
                <div className="glass-card p-6 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition">
                    <Notion className="w-24 h-24 text-white" />
                  </div>
                  <span className="text-xs font-bold text-slate-400 tracking-wider uppercase block mb-1">Conversion Sync Rate</span>
                  <span className="text-4xl font-extrabold text-violet-400 block mt-2">{analytics.overall_conversion.conversion_rate}%</span>
                  <div className="flex items-center gap-1.5 mt-3">
                    <span className="text-xs text-slate-400">{analytics.overall_conversion.completed_reels} completed</span>
                    <span className="text-xs text-slate-500">•</span>
                    <span className="text-xs text-rose-400">{analytics.overall_conversion.failed_reels} failed</span>
                  </div>
                </div>

              </div>

              {/* GRID COLUMN SECTION: FORM AND LOGS */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Form submit area (Left/Center) */}
                <div className="lg:col-span-1 space-y-6">
                  <div className="glass-card p-6">
                    <h3 className="font-bold text-lg text-white mb-2 flex items-center gap-2">
                      <PlayCircle className="w-5 h-5 text-violet-400" />
                      Queue New Reel
                    </h3>
                    <p className="text-xs text-slate-400 mb-6">
                      Admin dispatch utility. Manually push an Instagram Reel URL directly into the processing worker pipelines.
                    </p>

                    <form onSubmit={handleUrlSubmit} className="space-y-4">
                      <div>
                        <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1.5 tracking-wider">Instagram Reel URL *</label>
                        <input
                          id="form-reel-url"
                          type="url"
                          required
                          value={reelUrlInput}
                          onChange={(e) => setReelUrlInput(e.target.value)}
                          placeholder="https://www.instagram.com/reel/..."
                          className="w-full bg-[#08090d] border border-slate-800 rounded-xl px-4 py-3 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/60 transition"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1.5 tracking-wider">Creator Username (Optional)</label>
                        <input
                          id="form-creator-name"
                          type="text"
                          value={creatorInput}
                          onChange={(e) => setCreatorInput(e.target.value)}
                          placeholder="e.g. tech_guide_ai"
                          className="w-full bg-[#08090d] border border-slate-800 rounded-xl px-4 py-3 text-sm placeholder-slate-600 focus:outline-none focus:border-violet-500/60 transition"
                        />
                      </div>

                      {formStatus.type && (
                        <div className={`p-3 rounded-lg border text-xs ${
                          formStatus.type === "success" 
                            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
                            : "bg-rose-500/10 border-rose-500/20 text-rose-400"
                        }`}>
                          {formStatus.msg}
                        </div>
                      )}

                      <button
                        id="btn-submit-reel-form"
                        type="submit"
                        className="w-full py-3 bg-violet-600 hover:bg-violet-500 active:scale-[0.98] text-white rounded-xl font-semibold text-sm transition flex items-center justify-center gap-2"
                      >
                        <Send className="w-4 h-4" />
                        Dispatch Worker Job
                      </button>
                    </form>
                  </div>
                  
                  {/* Category distributions graphic block */}
                  <div className="glass-card p-6">
                    <h3 className="font-bold text-base text-white mb-4">Category Brain Mapping</h3>
                    {analytics.category_distribution.length === 0 ? (
                      <div className="text-center py-6 text-xs text-slate-500">No resources classified yet.</div>
                    ) : (
                      <div className="space-y-3.5">
                        {analytics.category_distribution.map(cat => {
                          const percent = Math.min(100, Math.round((cat.count / analytics.total_resources) * 100)) || 0;
                          return (
                            <div key={cat.category}>
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className="text-slate-300 font-medium">{cat.category}</span>
                                <span className="text-slate-400 font-bold">{cat.count} files ({percent}%)</span>
                              </div>
                              <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                                <div 
                                  className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-400" 
                                  style={{ width: `${percent}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* Live execution logs ticker (Right 2 cols) */}
                <div className="lg:col-span-2 glass-card p-6 flex flex-col">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="font-bold text-lg text-white flex items-center gap-2">
                        <Terminal className="w-5 h-5 text-violet-400" />
                        Live Pipeline Audit
                      </h3>
                      <span className="text-[10px] text-slate-400 uppercase tracking-widest block mt-0.5">Real-time task tracker logs</span>
                    </div>
                    <button 
                      onClick={() => setActiveTab("logs")}
                      className="text-xs text-violet-400 hover:text-violet-300 font-medium"
                    >
                      View All
                    </button>
                  </div>

                  <div className="space-y-4 flex-1 overflow-y-auto max-h-[380px] pr-2">
                    {logs.slice(0, 7).map((log, index) => (
                      <div 
                        key={log.id || index}
                        className="p-4 bg-slate-900/40 border border-slate-800/80 hover:border-slate-800 rounded-xl transition flex gap-3 text-xs"
                      >
                        <div className="mt-0.5">
                          {log.status === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                          {log.status === "error" && <AlertCircle className="w-4 h-4 text-rose-400 animate-pulse" />}
                          {log.status === "warning" && <AlertCircle className="w-4 h-4 text-amber-400" />}
                          {log.status === "info" && <RotateCw className="w-4 h-4 text-blue-400 animate-spin" />}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-200 capitalize">{log.step_name.replace("_", " ")}</span>
                            <span className="text-[10px] text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-slate-300 leading-relaxed">{log.message}</p>
                          {log.error_message && (
                            <pre className="p-2 bg-rose-950/20 border border-rose-900/30 text-[10px] text-rose-300 rounded font-mono mt-2 overflow-x-auto">
                              {log.error_message}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* TAB 2: REELS TAB */}
          {activeTab === "reels" && !searchActive && (
            <div className="glass-card p-6 animate-fade-in">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="font-bold text-lg text-white">Pipeline Execution Status</h3>
                  <p className="text-xs text-slate-400 mt-1">Full state-machine trackers for shared Reels.</p>
                </div>
              </div>

              {reels.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">No Reels queued in database.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-widest text-[10px]">
                        <th className="py-3.5 px-4 font-bold">Creator</th>
                        <th className="py-3.5 px-4 font-bold">Reel URL</th>
                        <th className="py-3.5 px-4 font-bold">Target Keywords</th>
                        <th className="py-3.5 px-4 font-bold">State Status</th>
                        <th className="py-3.5 px-4 font-bold">Created Date</th>
                        <th className="py-3.5 px-4 font-bold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {reels.map(r => (
                        <tr key={r.id} className="hover:bg-slate-900/30 transition">
                          <td className="py-4 px-4 font-semibold text-white">
                            {r.creator_name ? `@${r.creator_name}` : <span className="text-slate-500 italic">extracting...</span>}
                          </td>
                          <td className="py-4 px-4">
                            <a 
                              href={r.reel_url} 
                              target="_blank" 
                              rel="noreferrer"
                              className="text-violet-400 hover:text-violet-300 flex items-center gap-1"
                            >
                              Open Reel <ExternalLink className="w-3 h-3" />
                            </a>
                          </td>
                          <td className="py-4 px-4">
                            {r.comment_keyword ? (
                              <span className="font-mono bg-violet-500/10 px-2 py-0.5 border border-violet-500/20 text-violet-400 rounded">
                                {r.comment_keyword}
                              </span>
                            ) : (
                              <span className="text-slate-500 italic">checking...</span>
                            )}
                          </td>
                          <td className="py-4 px-4">{getStatusBadge(r.status)}</td>
                          <td className="py-4 px-4 text-slate-400">{new Date(r.created_at).toLocaleString()}</td>
                          <td className="py-4 px-4 text-right">
                            {r.status === "failed" || r.status === "dm_timeout" ? (
                              <button 
                                onClick={() => triggerRetry(r.id)}
                                className="px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/30 text-violet-400 border border-violet-500/30 rounded-lg transition flex items-center gap-1 ml-auto"
                              >
                                <RefreshCw className="w-3 h-3" /> Retry Task
                              </button>
                            ) : (
                              <span className="text-slate-500 text-[10px] uppercase font-bold tracking-wider">in loop</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: HARVESTED RESOURCES */}
          {activeTab === "resources" && !searchActive && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-lg text-white">Harvested Second Brain Files</h3>
                  <p className="text-xs text-slate-400 mt-1">Resource vaults uploaded to Supabase Storage and synced to Notion.</p>
                </div>
              </div>

              {resources.length === 0 ? (
                <div className="text-center py-12 glass-card text-slate-500 text-sm">
                  No resources harvested from Instagram DM threads yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {resources.map(res => (
                    <div key={res.id} className="glass-card p-5 flex flex-col justify-between h-[230px]">
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-[10px] font-extrabold text-violet-400 bg-violet-500/10 px-2.5 py-0.5 border border-violet-500/20 rounded-full tracking-wider uppercase">
                            {res.category}
                          </span>
                          <span className="text-[10px] text-slate-500 font-semibold">
                            {new Date(res.received_at).toLocaleDateString()}
                          </span>
                        </div>
                        <h4 className="font-bold text-white mb-1.5 text-sm line-clamp-1 flex items-center gap-1.5">
                          <FileText className="w-4 h-4 text-blue-400 shrink-0" />
                          {res.file_name}
                        </h4>
                        <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                          {res.resource_text || "No accompanying message context extracted."}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 pt-4 border-t border-slate-800/80">
                        <a 
                          href={res.resource_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 hover:text-white text-slate-200 text-xs rounded-lg transition-all flex items-center justify-center gap-1"
                        >
                          <ExternalLink className="w-3.5 h-3.5" /> Download / Link
                        </a>
                        
                        {res.notion_synced ? (
                          <span className="px-3 py-2 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Synced
                          </span>
                        ) : (
                          <button
                            onClick={() => triggerNotionSync(res.id)}
                            className="px-3 py-2 text-xs bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-lg transition-all"
                          >
                            Sync Notion
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: TRACKED CREATORS */}
          {activeTab === "creators" && !searchActive && (
            <div className="glass-card p-6 animate-fade-in">
              <div className="mb-6">
                <h3 className="font-bold text-lg text-white">Tracked Creator Relationships</h3>
                <p className="text-xs text-slate-400 mt-1">Avoid follow penalties. Relationships map directly to shared Reel triggers.</p>
              </div>

              {creators.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">No creators followed in relationship logs.</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {creators.map(c => (
                    <div key={c.id} className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs">
                      <div>
                        <h4 className="font-bold text-slate-200 text-sm">@{c.creator_name}</h4>
                        <div className="flex items-center gap-3 text-[10px] text-slate-400 mt-1 font-semibold">
                          <span>Reels Forwarded: {c.total_reels}</span>
                          <span>•</span>
                          <span>Resources Harvested: {c.total_resources}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {c.followed ? (
                          <span className="px-2.5 py-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 text-emerald-400">
                            FOLLOWING
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-full border border-slate-700 bg-slate-800 text-slate-400">
                            UNFOLLOWED
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: SYSTEM AUDIT LOGS */}
          {activeTab === "logs" && !searchActive && (
            <div className="glass-card p-6 animate-fade-in">
              <div className="mb-6">
                <h3 className="font-bold text-lg text-white">Execution Process Streams</h3>
                <p className="text-xs text-slate-400 mt-1">Chronological run traces of background worker loops.</p>
              </div>

              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                {logs.map((log, index) => (
                  <div 
                    key={log.id || index}
                    className="p-4 bg-slate-900/30 border border-slate-800/60 rounded-xl flex gap-3 text-xs"
                  >
                    <div className="mt-0.5">
                      {log.status === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                      {log.status === "error" && <AlertCircle className="w-4 h-4 text-rose-400 animate-pulse" />}
                      {log.status === "warning" && <AlertCircle className="w-4 h-4 text-amber-400" />}
                      {log.status === "info" && <RotateCw className="w-4 h-4 text-blue-400 animate-spin" />}
                    </div>
                    
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-extrabold text-slate-200 tracking-wide uppercase text-[10px] bg-slate-800 px-2 py-0.5 rounded">
                          {log.step_name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-semibold">{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-slate-300 leading-relaxed mt-1">{log.message}</p>
                      {log.error_message && (
                        <pre className="p-3 bg-rose-950/20 border border-rose-900/30 text-[10px] text-rose-300 rounded font-mono mt-2 overflow-x-auto">
                          {log.error_message}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
        
        {/* FOOTER */}
        <footer className="border-t border-slate-800/80 bg-[#040507] py-6 px-10 text-center text-xs text-slate-500">
          Reelise Core MVP Version 1.0.0. Designed for low-footprint, single-admin Instagram resource auto-harvesting.
        </footer>

      </main>

    </div>
  );
}
