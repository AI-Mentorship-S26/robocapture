"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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
type RLModel = "random" | "deep_contextual_bandit" | "contextual_bandit" | "sarsa" | "dqn" | "ppo" | "reinforce" | "aac" | "tiny_sac";
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
  const router = useRouter();

  const handleLogout = useCallback(async () => {
    await supabase.auth.signOut();
    router.push("/login");
  }, [router]);

  const [user, setUser]           = useState<{ email?: string; id?: string } | null>(null);
  const [wsStatus, setWsStatus]   = useState<WsStatus>("connecting");
  const [activeView, setActiveView] = useState<NavView>("live");
  const [activeModel, setActiveModel] = useState<RLModel>("deep_contextual_bandit");
  const [stats, setStats]         = useState({ sent: 18, skipped: 34, epsilon: 0.22 });
  const [frameNumber, setFrameNumber] = useState(1247);
const [stateVector, setStateVector] = useState<StateVector>({
    entropy: 0.72, edgeDensity: 0.55, novelty: 0.88, opticalFlow: 0.31,
  });
  const [history, setHistory]     = useState<HistoryEntry[]>(SEED_HISTORY);
  const [rewardData, setRewardData] = useState(SEED_REWARD_HISTORY);
  const [receivedAgo, setReceivedAgo] = useState("waiting...");
  const [wsMessage, setWsMessage] = useState<string>("");
  const [capturedImageSrc, setCapturedImageSrc] = useState<string>("");
  const [actionTaken, setActionTaken] = useState(false);
  const [currentImageId, setCurrentImageId] = useState<string>("");
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [navigationStarted, setNavigationStarted] = useState(false);


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
          setActionTaken(false);
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


  const sendAction = useCallback((action: "+R" | "-P" | "skip") => {
    if (!capturedImageSrc || actionTaken) return;
    setActionTaken(true);
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
        console.log(`Sent: ${feedback}:${currentImageId}`);
      }
    } else {
      setStats((s) => ({ ...s, skipped: s.skipped + 1 }));
    }
  }, [capturedImageSrc, actionTaken, currentImageId]);


  const handleCaptureImage = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send("captureImage");
      setWsMessage("Capture request sent…");
    } else {
      setWsMessage("Not connected — check if the backend is running.");
    }
  }, []);

  const handleStartNavigation = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send("startNavigation");
      setNavigationStarted(true);
      setWsMessage("Navigation started!");
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
          <StatPill label="Model" value={activeModel} />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] text-[11px] text-white/60">
            <span className={`w-1.5 h-1.5 rounded-full ${wsColor}`} />
            {wsLabel}
          </div>
          {user && (
            <button
              onClick={() => setShowLogoutModal(true)}
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
                { id: "random",    name: "Random",                sub: "Baseline · no learning" },
                { id: "deep_contextual_bandit", name: "Deep Contextual Bandit", sub: "DCB · neural network" },
                { id: "contextual_bandit", name: "Contextual Bandit", sub: "CB · sample efficient" },
                { id: "sarsa",     name: "Deep SARSA",             sub: "SARSA · on-policy" },
                { id: "dqn",       name: "Deep Q-Network",         sub: "DQN · off-policy" },
                { id: "ppo",       name: "Proximal Policy Opt.",   sub: "PPO · policy gradient" },
                { id: "reinforce", name: "REINFORCE",              sub: "PG · Monte Carlo" },
                { id: "aac",       name: "Advantage Actor-Critic", sub: "AAC · actor-critic" },
                { id: "tiny_sac",  name: "Tiny SAC",               sub: "SAC · entropy-based" },
              ] as { id: RLModel; name: string; sub: string }[]).map(({ id, name, sub }) => (
                <button
                  key={id}
                  onClick={() => {
                    setActiveModel(id)
                    if (socketRef.current?.readyState === WebSocket.OPEN) {
                      socketRef.current.send(`setModel:${id}`);
                      console.log(`Sent: setModel:${id}`);
                    }
                  }}
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
              onClick={handleLogout}
              className="flex items-center gap-2 px-2.5 py-2 mt-3 w-full rounded-md text-white/25 hover:text-rose-400/70 hover:bg-rose-500/[0.05] transition-colors duration-150 cursor-pointer text-xs"
            >
              <LogOutIcon size={13} />Sign out
            </button>
          </div>
        </aside>

        {/* ── Center Workspace ──────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-y-auto px-6 py-5 gap-5 min-w-0 bg-[#0F0F12] scrollbar-dark">

          <div className="flex items-center justify-between">
            <h1 className="text-sm font-semibold text-white/60">
              Session <span className="font-mono text-blue-400">#0042</span>
              <span className="text-white/20 mx-2">·</span>Mars Exploration A
            </h1>
          </div>

          {/* ── Reward History View ─────────────────────────────────────────── */}
          {activeView === "rewards" && (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
              <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
                <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">Reward History</span>
                <span className="font-mono text-[11px] text-white/30">{rewardData.length} steps</span>
              </div>
              <div className="p-5 flex flex-col gap-3">
                {/* Large bar chart */}
                <div className="h-48">
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
                      <Bar dataKey="reward" radius={[3, 3, 0, 0]}>
                        {rewardData.map((_, index) => (
                          <Cell
                            key={index}
                            fill={
                              index === rewardData.length - 1
                                ? "#3B82F6"
                                : `rgba(59,130,246,${0.2 + (index / rewardData.length) * 0.6})`
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono text-[9px] text-white/15">earliest</span>
                  <span className="font-mono text-[9px] text-white/15">latest</span>
                </div>
                {/* Per-step rows */}
                <div className="mt-2 flex flex-col gap-1">
                  <div className="flex items-center gap-3 px-1 pb-1 border-b border-white/[0.04]">
                    <span className="text-[9px] text-white/20 uppercase tracking-widest w-8">Step</span>
                    <span className="text-[9px] text-white/20 uppercase tracking-widest flex-1">Reward</span>
                    <span className="text-[9px] text-white/20 uppercase tracking-widest w-10 text-right">Value</span>
                  </div>
                  {[...rewardData].reverse().map((entry, index) => (
                    <div key={index} className="flex items-center gap-3 px-1 py-1.5 rounded-md hover:bg-white/[0.03] transition-colors">
                      <span className="font-mono text-[11px] text-white/30 w-8">{entry.step}</span>
                      <div className="flex-1 h-[4px] rounded-full bg-white/[0.05] overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${entry.reward * 100}%`,
                            backgroundColor: entry.reward >= 0.7 ? "#10B981" : entry.reward >= 0.4 ? "#3B82F6" : "#F59E0B",
                          }}
                        />
                      </div>
                      <span className="font-mono text-[11px] text-white/50 w-10 text-right">{entry.reward.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Live Feed View ──────────────────────────────────────────────── */}
          {activeView === "live" && (<>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col relative">
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

              
              {/* Navigation / Capture buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleStartNavigation}
                  disabled={navigationStarted}
                  className="flex-1 py-2.5 rounded-full bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all"
                >
                  {navigationStarted ? "Navigation Running..." : "Start Navigation"}
                </button>
                <button
                  onClick={handleCaptureImage}
                  disabled={navigationStarted}
                  className="flex-1 py-2.5 rounded-full bg-white/90 text-black text-sm font-semibold hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all"
                >
                  Capture Image
                </button>
              </div>

            </div>

            {/* Login required overlay */}
            {!user && (
              <div className="absolute inset-0 rounded-xl bg-[#0F0F12]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3">
                <p className="text-[15px] font-semibold text-white/80">Login required</p>
                <p className="text-[12px] text-white/40 text-center px-6">You must be logged in to capture images.</p>
                <a
                  href="/login"
                  className="mt-1 px-6 py-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all"
                >
                  Go to Login
                </a>
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5">
            <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-4">Your Feedback</p>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => sendAction("+R")}
                disabled={!capturedImageSrc || actionTaken}
                className="flex items-center justify-center gap-2 py-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm font-semibold hover:bg-emerald-500/15 hover:border-emerald-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
              >
                <span className="text-base font-bold leading-none">+</span>Reward
              </button>
              <button
                onClick={() => sendAction("-P")}
                disabled={!capturedImageSrc || actionTaken}
                className="flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-sm font-semibold hover:bg-rose-500/15 hover:border-rose-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
              >
                <span className="text-base font-bold leading-none">−</span>Penalty
              </button>
              <button
                onClick={() => sendAction("skip")}
                disabled={!capturedImageSrc || actionTaken}
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
          </>)}

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

      {/* ── Logout Confirmation Modal ───────────────────────────────────────── */}
      {showLogoutModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
          onClick={() => setShowLogoutModal(false)}
        >
          <div
            className="w-80 rounded-xl border border-white/[0.10] bg-[#16161A] shadow-2xl p-6 flex flex-col gap-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col gap-1.5">
              <h2 className="text-sm font-semibold text-white/90">Log out</h2>
              <p className="text-xs text-white/40">Are you sure you want to end your session?</p>
            </div>
            <div className="flex gap-2.5 justify-end">
              <button
                onClick={() => setShowLogoutModal(false)}
                className="px-4 py-1.5 rounded-lg text-xs text-white/50 border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] hover:text-white/70 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => { handleLogout(); setShowLogoutModal(false); }}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold text-white bg-rose-500/80 border border-rose-500/40 hover:bg-rose-500 transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <LogOutIcon size={12} />
                Log out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
