"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { supabase } from "@/utils/supabase/client";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from "recharts";

// ─── Types ───────────────────────────────────────────────────────────────────

type NavView = "live" | "gallery" | "rewards" | "logs";
type RLModel = "dqn" | "mab";
type FrameAction = "+R" | "-P" | null;
type WsStatus = "connecting" | "connected" | "disconnected" | "error";

interface HistoryEntry {
  id: number;
  timestamp: string;
  status: "sent" | "skipped";
  action: FrameAction;
}

interface StateVector {
  entropy: number;
  edgeDensity: number;
  novelty: number;
  opticalFlow: number;
}

// ─── Inline SVG Icons ────────────────────────────────────────────────────────

const MonitorIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8m-4-4v4" />
  </svg>
);
const GridIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);
const TrendingUpIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
  </svg>
);
const ClockIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);
const LogOutIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);
const CpuIcon = ({ size = 16, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
  </svg>
);
const ImageIcon = ({ size = 14, className = "" }: { size?: number; className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" />
  </svg>
);

// ─── Seed Data ────────────────────────────────────────────────────────────────

const SEED_HISTORY: HistoryEntry[] = [
  { id: 1, timestamp: "12:04:31", status: "sent",    action: "+R" },
  { id: 2, timestamp: "12:04:28", status: "skipped", action: null },
  { id: 3, timestamp: "12:04:24", status: "sent",    action: "-P" },
  { id: 4, timestamp: "12:04:19", status: "sent",    action: "+R" },
  { id: 5, timestamp: "12:04:15", status: "skipped", action: null },
  { id: 6, timestamp: "12:04:10", status: "sent",    action: "+R" },
  { id: 7, timestamp: "12:04:06", status: "sent",    action: "+R" },
  { id: 8, timestamp: "12:04:01", status: "skipped", action: null },
];

const SEED_REWARD_HISTORY = [
  { step: "S1",  reward: 0.2  },
  { step: "S2",  reward: 0.3  },
  { step: "S3",  reward: 0.5  },
  { step: "S4",  reward: 0.4  },
  { step: "S5",  reward: 0.6  },
  { step: "S6",  reward: 0.7  },
  { step: "S7",  reward: 0.65 },
  { step: "S8",  reward: 0.8  },
  { step: "S9",  reward: 0.75 },
  { step: "S10", reward: 0.9  },
  { step: "S11", reward: 0.85 },
  { step: "S12", reward: 1.0  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.04] border border-white/[0.06]">
      <span className="text-[10px] text-white/30 uppercase tracking-widest">{label}</span>
      <span className="font-mono text-xs text-white/70">{value}</span>
    </div>
  );
}

function StateBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-white/40 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-[3px] rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${value * 100}%`, backgroundColor: color }}
        />
      </div>
      <span className="font-mono text-[11px] text-white/50 w-8 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

function HistoryRow({ entry }: { entry: HistoryEntry }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors duration-150 cursor-pointer group">
      <div className="w-9 h-9 rounded-md bg-white/[0.05] border border-white/[0.06] flex items-center justify-center shrink-0 group-hover:border-white/10 transition-colors">
        <ImageIcon size={12} className="text-white/20" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-mono text-[11px] text-white/50">{entry.timestamp}</p>
        <p className={`text-[10px] mt-0.5 ${entry.status === "sent" ? "text-emerald-400/70" : "text-white/25"}`}>
          {entry.status === "sent" ? "Sent" : "Skipped"}
        </p>
      </div>
      <div className="shrink-0">
        {entry.action === "+R" && (
          <span className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">+R</span>
        )}
        {entry.action === "-P" && (
          <span className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">−P</span>
        )}
        {entry.action === null && (
          <span className="font-mono text-[10px] text-white/15">—</span>
        )}
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const socketRef = useRef<WebSocket | null>(null);

  const [user, setUser]           = useState<{ email?: string; id?: string } | null>(null);
  const [wsStatus, setWsStatus]   = useState<WsStatus>("connecting");
  const [activeView, setActiveView] = useState<NavView>("live");
  const [activeModel, setActiveModel] = useState<RLModel>("dqn");
  const [stats, setStats]         = useState({ sent: 18, skipped: 34, epsilon: 0.22 });
  const [frameNumber, setFrameNumber] = useState(1247);
const [stateVector, setStateVector] = useState<StateVector>({
    entropy: 0.72, edgeDensity: 0.55, novelty: 0.88, opticalFlow: 0.31,
  });
  const [history, setHistory]     = useState<HistoryEntry[]>(SEED_HISTORY);
  const [rewardData, setRewardData] = useState(SEED_REWARD_HISTORY);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [isVectorizing, setIsVectorizing] = useState(false);
  const [vectorStatus, setVectorStatus] = useState<{ success?: boolean; message?: string } | null>(null);
  const [receivedAgo, setReceivedAgo] = useState("waiting...");
  const [wsMessage, setWsMessage] = useState<string>("");
  const [capturedImageSrc, setCapturedImageSrc] = useState<string>("");
  const [currentImageId, setCurrentImageId] = useState<string>("");

  // Auth
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setUser(s?.user ?? null));
    return () => sub.subscription.unsubscribe();
  }, []);

  // WebSocket
  useEffect(() => {
    const socket = new WebSocket("ws://localhost:5081/ws");
    socket.onopen    = () => setWsStatus("connected");
    socket.onmessage = (event) => {
      setReceivedAgo("0.1s ago");
      try {
        const data = JSON.parse(event.data);
        if (data.type === "image") {
          setWsMessage("Image received!");
          setCapturedImageSrc(`data:${data.format};base64,${data.data}`);
          setCurrentImageId(data.image_id); 
          setFrameNumber((n) => n + 1);
        } else if (data.type === "no_send") {
          setWsMessage(data.message);
        } else if (data.type === "error") {
          setWsMessage(`Error: ${data.message}`);
        }
      } catch {
        // non-JSON message, ignore
      }
    };
    socket.onclose   = () => setWsStatus("disconnected");
    socket.onerror   = () => setWsStatus("error");
    socketRef.current = socket;
    return () => socket.close();
  }, []);

  // Paste image
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") !== -1) {
          const blob = items[i].getAsFile();
          if (blob) {
            setImageFile(blob);
            setImagePreview((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(blob); });
            setVectorStatus(null);
            setFrameNumber((n) => n + 1);
            setReceivedAgo("just now");
            setStateVector({
              entropy:     Math.round(Math.random() * 100) / 100,
              edgeDensity: Math.round(Math.random() * 100) / 100,
              novelty:     Math.round(Math.random() * 100) / 100,
              opticalFlow: Math.round(Math.random() * 100) / 100,
            });
          }
        }
      }
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, []);

  const sendAction = useCallback((action: "+R" | "-P" | "skip") => {
    if (!imagePreview) return;
    const historyAction: FrameAction = action === "skip" ? null : action;
    const status = action === "skip" ? "skipped" : "sent";
    const now = new Date();
    const ts = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}`;
    setHistory((prev) => [{ id: Date.now(), timestamp: ts, status, action: historyAction }, ...prev]);

    if (action !== "skip") {
      setStats((s) => ({ ...s, sent: s.sent + 1, epsilon: Math.max(0, parseFloat((s.epsilon - 0.01).toFixed(2))) }));
      const delta = action === "+R" ? 0.05 : -0.03;
      setRewardData((prev) => {
        const last = prev[prev.length - 1];
        const newVal = Math.max(0, Math.min(1, last.reward + delta));
        return [...prev.slice(-11), { step: `S${parseInt(last.step.slice(1)) + 1}`, reward: parseFloat(newVal.toFixed(2)) }];
      });
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        const feedback = action === "+R" ? "reward" : "punishment";
        socketRef.current.send(`${feedback}:${currentImageId}`);
      }
    } else {
      setStats((s) => ({ ...s, skipped: s.skipped + 1 }));
    }
  }, [imagePreview]);

  const handleVectorize = useCallback(async () => {
    if (!imageFile) return;
    setIsVectorizing(true);
    setVectorStatus(null);
    const formData = new FormData();
    formData.append("image", imageFile);
    if (user?.id) formData.append("userId", user.id);
    try {
      const res  = await fetch("/api/vectorize", { method: "POST", body: formData });
      const data = await res.json();
      setVectorStatus({ success: res.ok, message: res.ok ? data.message : data.error });
    } catch (e: unknown) {
      setVectorStatus({ success: false, message: e instanceof Error ? e.message : "Unknown error" });
    } finally {
      setIsVectorizing(false);
    }
  }, [imageFile, user]);

  const handleCaptureImage = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send("captureImage");
      setWsMessage("Capture request sent…");
    } else {
      setWsMessage("Not connected — check if the backend is running.");
    }
  }, []);

  const wsColor = { connected: "bg-emerald-400", connecting: "bg-yellow-400 animate-pulse", disconnected: "bg-white/20", error: "bg-rose-400" }[wsStatus];
  const wsLabel = { connected: "Robot connected", connecting: "Connecting…", disconnected: "Disconnected", error: "Connection error" }[wsStatus];

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "#0F0F12", fontFamily: "'Fira Sans', sans-serif" }}>

      {/* ── Top Bar ────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 h-12 shrink-0 border-b border-white/[0.06] bg-[#0F0F12]/80 backdrop-blur-md z-20">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
            <CpuIcon size={12} className="text-blue-400" />
          </div>
          <span className="text-sm font-semibold text-white/90 tracking-tight">
            Robo<span className="text-blue-400">Capture</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-2">
          <span className="font-mono text-[11px] text-white/30">Session</span>
          <span className="font-mono text-[11px] text-white/60">#0042 · Mars Exploration A</span>
          <div className="w-px h-3 bg-white/[0.08] mx-2" />
          <StatPill label="Sent"    value={stats.sent} />
          <StatPill label="Skipped" value={stats.skipped} />
          <StatPill label="ε ="     value={stats.epsilon.toFixed(2)} />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] text-[11px] text-white/60">
            <span className={`w-1.5 h-1.5 rounded-full ${wsColor}`} />
            {wsLabel}
          </div>
          {user && (
            <button
              onClick={() => supabase.auth.signOut()}
              title="Log out"
              className="w-7 h-7 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 text-[10px] font-bold uppercase hover:bg-blue-500/30 transition-colors cursor-pointer"
            >
              {user.email?.[0]?.toUpperCase() ?? "U"}
            </button>
          )}
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left Sidebar ─────────────────────────────────────────────────── */}
        <aside className="w-52 shrink-0 flex flex-col border-r border-white/[0.06] bg-[#0D0D10]/50">
          <div className="flex-1 px-3 py-4">
            <p className="text-[9px] font-semibold text-white/20 tracking-[0.2em] uppercase px-2 mb-2">Views</p>
            <nav className="flex flex-col gap-0.5">
              {([
                { id: "live",    label: "Live feed",      Icon: MonitorIcon },
                { id: "gallery", label: "Image gallery",  Icon: GridIcon },
                { id: "rewards", label: "Reward history", Icon: TrendingUpIcon },
                { id: "logs",    label: "Session logs",   Icon: ClockIcon },
              ] as { id: NavView; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }[]).map(({ id, label, Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveView(id)}
                  className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs transition-colors duration-150 cursor-pointer w-full text-left ${
                    activeView === id
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      : "text-white/40 hover:text-white/70 hover:bg-white/[0.04] border border-transparent"
                  }`}
                >
                  <Icon size={14} />{label}
                </button>
              ))}
            </nav>
          </div>

          {/* RL Model */}
          <div className="px-3 py-4 border-t border-white/[0.06]">
            <p className="text-[9px] font-semibold text-white/20 tracking-[0.2em] uppercase px-2 mb-2">RL Model</p>
            <div className="flex flex-col gap-1.5">
              {([
                { id: "dqn", name: "Deep Q-Network",     sub: "DQL · stateful" },
                { id: "mab", name: "Multi-Armed Bandit",  sub: "MAB · lightweight" },
              ] as { id: RLModel; name: string; sub: string }[]).map(({ id, name, sub }) => (
                <button
                  key={id}
                  onClick={() => setActiveModel(id)}
                  className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all duration-150 cursor-pointer text-left w-full border ${
                    activeModel === id
                      ? "bg-blue-500/10 border-blue-500/25 text-blue-400"
                      : "border-transparent text-white/30 hover:text-white/50 hover:bg-white/[0.03]"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${activeModel === id ? "bg-blue-400" : "bg-white/15"}`} />
                  <div>
                    <p className="text-[11px] font-medium leading-tight">{name}</p>
                    <p className="font-mono text-[9px] mt-0.5 opacity-60">{sub}</p>
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => supabase.auth.signOut()}
              className="flex items-center gap-2 px-2.5 py-2 mt-3 w-full rounded-md text-white/25 hover:text-rose-400/70 hover:bg-rose-500/[0.05] transition-colors duration-150 cursor-pointer text-xs"
            >
              <LogOutIcon size={13} />Sign out
            </button>
          </div>
        </aside>

        {/* ── Center Workspace ──────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-y-auto px-6 py-5 gap-5 min-w-0">

          <div className="flex items-center justify-between">
            <h1 className="text-sm font-semibold text-white/60">
              Session <span className="font-mono text-blue-400">#0042</span>
              <span className="text-white/20 mx-2">·</span>Mars Exploration A
            </h1>
          </div>

          {/* Current Frame — 2-column split */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

            {/* Left — WebSocket / Capture */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
              <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
                <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">WebSocket</span>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-full border border-white/[0.08] bg-white/[0.04]">
                  <span className={`w-1.5 h-1.5 rounded-full ${wsColor}`} />
                  <span className="text-[10px] text-white/50">{wsLabel}</span>
                </div>
              </div>
              <div className="p-5 flex flex-col gap-4 flex-1">
                {/* Status / message box */}
                <div className="p-3 rounded-lg bg-[#161619] border border-white/[0.06] min-h-[48px] flex items-center justify-center">
                  <p className="text-[11px] font-mono text-white/40 italic text-center">
                    {wsMessage ? `Last message: ${wsMessage}` : "Waiting for backend response…"}
                  </p>
                </div>

                {/* Captured image */}
                <div className="w-full aspect-video rounded-lg overflow-hidden bg-[#161619] border border-white/[0.06] flex items-center justify-center">
                  {capturedImageSrc ? (
                    <img src={capturedImageSrc} alt="Captured from Pi" className="w-full h-full object-contain" />
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-10 h-10 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                        <MonitorIcon size={18} className="text-white/15" />
                      </div>
                      <p className="text-[11px] text-white/20">No capture yet</p>
                    </div>
                  )}
                </div>

                {/* Frame meta */}
                <div className="flex items-center gap-3 flex-wrap justify-center">
                  <span className="font-mono text-[11px] text-white/30">
                    Frame <span className="text-white/50">#{frameNumber.toLocaleString()}</span>
                    <span className="text-white/20 mx-2">·</span>640×480
                  </span>
                  <span className="text-[11px] text-white/25">Received {receivedAgo}</span>
                </div>

                {/* Capture button */}
                <button
                  onClick={handleCaptureImage}
                  className="w-full py-2.5 rounded-full bg-white/90 dark:bg-white text-black text-sm font-semibold hover:opacity-80 active:scale-95 transition-all"
                >
                  Capture Image
                </button>
              </div>
            </div>

            {/* Right — Image Vectorizer */}
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
              <div className="px-4 py-3 border-b border-white/[0.05]">
                <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">Image Vectorizer</span>
              </div>
              <div className="p-5 flex flex-col gap-4 flex-1">
                {user ? (
                  <>
                    <p className="text-[11px] text-white/30 text-center">
                      Paste an image (Ctrl+V) anywhere to vectorize and send to Supabase.
                    </p>

                    {/* Paste preview */}
                    <div className="flex-1 min-h-[160px] border-2 border-dashed border-white/[0.08] rounded-lg flex items-center justify-center overflow-hidden">
                      {imagePreview ? (
                        <img src={imagePreview} alt="Pasted preview" className="max-h-[180px] object-contain rounded" />
                      ) : (
                        <p className="text-[11px] text-white/20">No image pasted yet</p>
                      )}
                    </div>

                    {vectorStatus && (
                      <p className={`text-[11px] font-mono text-center ${vectorStatus.success ? "text-emerald-400" : "text-rose-400"}`}>
                        {vectorStatus.message}
                      </p>
                    )}

                    <button
                      onClick={handleVectorize}
                      disabled={!imagePreview || isVectorizing}
                      className="w-full py-2.5 rounded-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:bg-blue-600 text-white text-sm font-semibold active:scale-95 transition-all"
                    >
                      {isVectorizing ? "Vectorizing & Saving…" : "Vectorize Image"}
                    </button>
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center flex-1 gap-4">
                    <p className="text-[13px] font-semibold text-white/60">Login required</p>
                    <p className="text-[11px] text-white/30 text-center">You must be logged in to vectorize images.</p>
                    <a
                      href="/login"
                      className="px-6 py-2.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all text-center"
                    >
                      Go to Login
                    </a>
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Action Bar */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5">
            <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-4">Your Feedback</p>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => sendAction("+R")}
                disabled={!capturedImageSrc}
                className="flex items-center justify-center gap-2 py-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm font-semibold hover:bg-emerald-500/15 hover:border-emerald-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
              >
                <span className="text-base font-bold leading-none">+</span>Reward
              </button>
              <button
                onClick={() => sendAction("-P")}
                disabled={!capturedImageSrc}
                className="flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-sm font-semibold hover:bg-rose-500/15 hover:border-rose-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
              >
                <span className="text-base font-bold leading-none">−</span>Penalty
              </button>
              <button
                onClick={() => sendAction("skip")}
                disabled={!capturedImageSrc}
                className="flex items-center justify-center py-3 rounded-xl border border-white/[0.08] bg-white/[0.03] text-white/50 text-sm font-semibold hover:bg-white/[0.07] hover:text-white/70 hover:border-white/15 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
              >
                Skip
              </button>
            </div>
          </div>

          {/* State Vector */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5">
            <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-4">
              Frame Features <span className="normal-case text-white/15 ml-1">(State Vector)</span>
            </p>
            <div className="flex flex-col gap-3.5">
              <StateBar label="Entropy"      value={stateVector.entropy}     color="#3B82F6" />
              <StateBar label="Edge density" value={stateVector.edgeDensity} color="#3B82F6" />
              <StateBar label="Novelty"      value={stateVector.novelty}     color="#10B981" />
              <StateBar label="Optical flow" value={stateVector.opticalFlow} color="#F59E0B" />
              <div className="flex items-center gap-3 mt-1 pt-3 border-t border-white/[0.04]">
                <span className="text-[11px] text-white/30 w-24 shrink-0">CNN embedding</span>
                <span className="font-mono text-[11px] text-white/20">1280-dim · MobileNetV2</span>
              </div>
            </div>
          </div>

        </main>

        {/* ── Right Activity Feed ───────────────────────────────────────────── */}
        <aside className="w-64 shrink-0 flex flex-col border-l border-white/[0.06] bg-[#0D0D10]/50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
            <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">History</span>
            <span className="font-mono text-[11px] text-white/30">{history.length + 44} frames</span>
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {history.map((entry) => (
              <HistoryRow key={entry.id} entry={entry} />
            ))}
          </div>

          {/* Cumulative Reward Chart */}
          <div className="border-t border-white/[0.06] px-4 py-4 shrink-0">
            <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-3">Cumulative Reward</p>
            <div className="h-16">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rewardData} barCategoryGap="20%">
                  <Tooltip
                    cursor={false}
                    contentStyle={{
                      background: "#161619",
                      border: "1px solid rgba(255,255,255,0.08)",
                      borderRadius: "6px",
                      fontSize: "10px",
                      color: "rgba(255,255,255,0.6)",
                      padding: "4px 8px",
                    }}
                    itemStyle={{ color: "#3B82F6" }}
                    labelStyle={{ display: "none" }}
                  />
                  <Bar dataKey="reward" radius={[2, 2, 0, 0]}>
                    {rewardData.map((_, index) => (
                      <Cell
                        key={index}
                        fill={
                          index === rewardData.length - 1
                            ? "#3B82F6"
                            : `rgba(59,130,246,${0.2 + (index / rewardData.length) * 0.5})`
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-between mt-1">
              <span className="font-mono text-[9px] text-white/15">early</span>
              <span className="font-mono text-[9px] text-white/15">now</span>
            </div>
          </div>
        </aside>

      </div>
    </div>
  );
}
