  "use client";

  import { useCallback, useEffect, useRef, useState } from "react";
  import { useRouter } from "next/navigation";
  import { supabase } from "@/utils/supabase/client";

  import {
    NavView,
    RLModel,
    FrameAction,
    WsStatus,
    GalleryImage,
    HistoryEntry,
    StateVector,
    SEED_HISTORY,
    SEED_REWARD_HISTORY,
  } from "@/types/dashboard";

  import Sidebar from "@/components/dashboard/Sidebar";
  import RightPanel from "@/components/dashboard/RightPanel";
  import LiveFeedView from "@/components/dashboard/LiveFeedView";
  import GalleryView from "@/components/dashboard/GalleryView";
  import RewardHistoryView from "@/components/dashboard/RewardHistoryView";
  import LogsView from "@/components/dashboard/LogsView";
  import { CpuIcon, LogOutIcon } from "@/components/dashboard/icons";

  //old
  //const PI_WS_URL = process.env.NEXT_PUBLIC_PI_WS_URL ?? "ws://raspberrypi.local:8765";

  //new
  const BACKEND_WS_URL = "ws://localhost:5081/ws";

  function StatPill({ label, value }: { label: string; value: string | number }) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.04] border border-white/[0.06]">
        <span className="text-[10px] text-white/30 uppercase tracking-widest">{label}</span>
        <span className="font-mono text-xs text-white/70">{value}</span>
      </div>
    );
  }

  export default function DashboardPage() {
    const socketRef = useRef<WebSocket | null>(null);
    const router = useRouter();

    const handleLogout = useCallback(async () => {
      await supabase.auth.signOut();
      router.push("/login");
    }, [router]);

    const [user, setUser] = useState<{ email?: string; id?: string } | null>(null);
    const [wsStatus, setWsStatus] = useState<WsStatus>("connecting");
    const [activeView, setActiveView] = useState<NavView>("live");
    const [activeModel, setActiveModel] = useState<RLModel>("deep_contextual_bandit");
    const [captureMode, setCaptureMode] = useState<"live" | "dataset">("live");
    const [currentCaptureMode, setCurrentCaptureMode] = useState<"live" | "dataset">("live");
    const [stats, setStats] = useState({ sent: 18, skipped: 34, epsilon: 0.22 });
    const [frameNumber, setFrameNumber] = useState(1247);
    const [stateVector, setStateVector] = useState<StateVector>({
      entropy: 0,
      edgeDensity: 0,
      novelty: 0,
      opticalFlow: 0,
    });
    const [history, setHistory] = useState<HistoryEntry[]>(SEED_HISTORY);
    const [rewardData, setRewardData] = useState(SEED_REWARD_HISTORY);
    const [receivedAgo, setReceivedAgo] = useState("waiting...");
    const [wsMessage, setWsMessage] = useState("");
    const [capturedImageSrc, setCapturedImageSrc] = useState("");
    const [actionTaken, setActionTaken] = useState(false);
    const [currentImageId, setCurrentImageId] = useState("");
    const [currentState, setCurrentState] = useState<number[]>([]);
    const [currentFeatures, setCurrentFeatures] = useState<Record<string, number>>({});
    const [currentPipelineWouldSend, setCurrentPipelineWouldSend] = useState<boolean | null>(null);
    const [showLogoutModal, setShowLogoutModal] = useState(false);
    const [navigationStarted, setNavigationStarted] = useState(false);

    const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "saved" | "error">("idle");
    const [saveTarget, setSaveTarget] = useState<"supabase" | "pi_dataset">("supabase");
    const [datasetSavedCount, setDatasetSavedCount] = useState(0);
    const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([]);
    const [galleryLoading, setGalleryLoading] = useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    useEffect(() => {
      supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
      const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setUser(s?.user ?? null));
      return () => sub.subscription.unsubscribe();
    }, []);

    useEffect(() => {
      let socket: WebSocket;
      try {
        socket = new WebSocket(BACKEND_WS_URL);
      } catch {
        setWsStatus("error");
        setWsMessage(`Invalid WebSocket URL: "${BACKEND_WS_URL}". Check NEXT_PUBLIC_PI_WS_URL in .env.local.`);
        return;
      }

      const connectionTimeout = setTimeout(() => {
        if (socket.readyState !== WebSocket.OPEN) {
          socket.close();
          setWsStatus("error");
          setWsMessage(
            `Connection timed out after 5s - could not reach ${BACKEND_WS_URL}. ` +
              `Check: (1) Pi server is running (python picam/pi_server.py), ` +
              `(2) Pi and this machine are on the same network, ` +
              `(3) IP in .env.local is correct.`
          );
        }
      }, 5000);

      socket.onopen = () => {
        clearTimeout(connectionTimeout);
        setWsStatus("connected");
        setWsMessage("");
      };

      socket.onmessage = (event) => {
        setReceivedAgo("0.1s ago");
        try {
          const data = JSON.parse(event.data);
          if (data.type === "image") {
            const messageCaptureMode = data.capture_mode === "dataset" ? "dataset" : "live";
            setUploadStatus("idle");
            setSaveTarget(messageCaptureMode === "dataset" ? "pi_dataset" : "supabase");
            setCurrentCaptureMode(messageCaptureMode);
            setCurrentPipelineWouldSend(
              typeof data.pipeline_would_send === "boolean" ? data.pipeline_would_send : null
            );
            setWsMessage(messageCaptureMode === "dataset" ? "Dataset image received!" : "Image received!");
            setCapturedImageSrc(`data:${data.format};base64,${data.data}`);
            setCurrentImageId(data.image_id);
            setCurrentState(data.state ?? []);
            setCurrentFeatures(data.features ?? {});
            setFrameNumber((n) => n + 1);
            setActionTaken(false);

            if (data.features) {
              const f = data.features;
              setStateVector({
                entropy: Math.min(f.change_pct / 100, 1),
                edgeDensity: Math.min(f.edge_count / 80000, 1),
                novelty: Math.min(f.sharpness / 2000, 1),
                opticalFlow: Math.min(f.saturation / 255, 1),
              });
            }
          } else if (data.type === "no_send") {
            setCurrentCaptureMode("live");
            setCurrentPipelineWouldSend(null);
            setWsMessage(data.message);
          } else if (data.type === "dataset_saved") {
            setSaveTarget("pi_dataset");
            setUploadStatus("saved");
            setDatasetSavedCount(data.saved_count ?? 0);
            setWsMessage(`Saved ${data.label} to Pi dataset (${data.saved_count ?? "?"} rows)`);
          } else if (data.type === "dataset_skipped") {
            setSaveTarget("pi_dataset");
            setUploadStatus("idle");
            setDatasetSavedCount(data.saved_count ?? 0);
            setWsMessage("Skipped this dataset row.");
          } else if (data.type === "error") {
            setUploadStatus("error");
            setWsMessage(`Error: ${data.message}`);
          }
        } catch {
          // Ignore non-JSON messages.
        }
      };

      socket.onclose = (event) => {
        clearTimeout(connectionTimeout);
        setWsStatus("disconnected");
        if (event.code === 1006) {
          setWsMessage(`Lost connection abnormally (code 1006) - Pi server likely crashed or is unreachable at ${BACKEND_WS_URL}.`);
        } else if (event.code !== 1000) {
          setWsMessage(`Disconnected (code ${event.code}). Refresh to reconnect.`);
        }
      };

      socket.onerror = () => {
        setWsStatus("error");
        setWsMessage(
          `WebSocket error - cannot connect to ${BACKEND_WS_URL}. ` +
            `Verify the Pi server is running and the IP/port is correct.`
        );
      };

      socketRef.current = socket;
      return () => {
        clearTimeout(connectionTimeout);
        socket.close();
      };
    }, []);

    const handleModelChange = useCallback((model: RLModel) => {
      setActiveModel(model);
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(`setModel:${model}`);
      }
    }, []);

    const sendAction = useCallback(
      async (action: "+R" | "-P" | "skip") => {
        if (!capturedImageSrc || actionTaken) return;
        setActionTaken(true);

        const historyAction: FrameAction = action === "skip" ? null : action;
        const status = action === "skip" ? "skipped" : "sent";
        const now = new Date();
        const ts = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
        setHistory((prev) => [{ id: Date.now(), timestamp: ts, status, action: historyAction }, ...prev]);

        if (currentCaptureMode === "dataset") {
          if (action === "skip") {
            if (socketRef.current?.readyState === WebSocket.OPEN) {
              socketRef.current.send(`datasetSkip:${currentImageId}`);
              setWsMessage("Dataset skip sent.");
            } else {
              setUploadStatus("error");
              setWsMessage("Not connected - could not skip dataset row.");
              setActionTaken(false);
            }
            return;
          }

          setSaveTarget("pi_dataset");
          setUploadStatus("uploading");
          if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(
              `datasetLabel:${currentImageId}:${action === "+R" ? "reward" : "punishment"}`
            );
          } else {
            setUploadStatus("error");
            setWsMessage("Not connected - could not save dataset label.");
            setActionTaken(false);
          }
          return;
        }

        if (action !== "skip") {
          setStats((s) => ({ ...s, sent: s.sent + 1 }));
          const delta = action === "+R" ? 0.05 : -0.03;
          setRewardData((prev) => {
            const last = prev[prev.length - 1];
            const newVal = Math.max(0, Math.min(1, last.reward + delta));
            return [
              ...prev.slice(-11),
              { step: `S${parseInt(last.step.slice(1), 10) + 1}`, reward: parseFloat(newVal.toFixed(2)) },
            ];
          });

          if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(`${action === "+R" ? "reward" : "punishment"}:${currentImageId}`);
          }

          if (user?.id) {
            setSaveTarget("supabase");
            setUploadStatus("uploading");
            const label = action === "+R" ? 1 : -1;
            try {
              if (action === "+R") {
                const storagePath = `${user.id}/${currentImageId}.jpg`;
                const res = await fetch(capturedImageSrc);
                const blob = await res.blob();
                const { error: storageError } = await supabase.storage
                  .from("robocapture-images")
                  .upload(storagePath, blob, { contentType: "image/jpeg", upsert: false });
                if (storageError && storageError.message !== "The resource already exists") {
                  setUploadStatus("error");
                  return;
                }
              }

              if (currentState.length < 8) {
                setUploadStatus("error");
                return;
              }

              const embedding = currentState.slice(7);
              const { error } = await supabase.from("image_vectors").insert({
                user_id: user.id,
                image_id: currentImageId,
                label,
                rl_model: activeModel,
                embedding: `[${embedding.join(",")}]`,
                features: currentFeatures,
              });
              setUploadStatus(error ? "error" : "saved");
            } catch {
              setUploadStatus("error");
            }
          }
        } else {
          setStats((s) => ({ ...s, skipped: s.skipped + 1 }));
        }
      },
      [capturedImageSrc, actionTaken, currentImageId, currentState, currentFeatures, user, activeModel, currentCaptureMode]
    );

    useEffect(() => {
      if (activeView !== "gallery" || !user?.id) return;
      let cancelled = false;

      const load = async () => {
        setGalleryLoading(true);
        try {
          const { data: rows, error } = await supabase
            .from("image_vectors")
            .select("image_id, rl_model, created_at")
            .eq("label", 1)
            .order("created_at", { ascending: false })
            .limit(200);

          if (cancelled || error || !rows?.length) {
            if (!cancelled) setGalleryImages([]);
            return;
          }

          const storagePaths = rows.map((r) => `${user.id}/${r.image_id}.jpg`);
          const { data: signed } = await supabase.storage
            .from("robocapture-images")
            .createSignedUrls(storagePaths, 3600);

          if (!cancelled && signed) {
            setGalleryImages(
              signed
                .map((u, i) => ({ signedUrl: u.signedUrl, row: rows[i] }))
                .filter(({ signedUrl }) => !!signedUrl)
                .map(({ signedUrl, row }) => ({
                  name: row.image_id,
                  url: signedUrl,
                  model: row.rl_model,
                  capturedAt: row.created_at,
                }))
            );
          }
        } finally {
          if (!cancelled) setGalleryLoading(false);
        }
      };

      load();
      return () => {
        cancelled = true;
      };
    }, [activeView, user?.id]);

    const handleCaptureImage = useCallback(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        const command = captureMode === "dataset" ? "captureDatasetImage" : "captureImage";
        socketRef.current.send(command);
        setWsMessage(captureMode === "dataset" ? "Dataset capture request sent..." : "Capture request sent...");
      } else {
        setWsMessage("Not connected - check if the backend is running.");
      }
    }, [captureMode]);

    const handleStartNavigation = useCallback(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send("startNavigation");
        setNavigationStarted(true);
        setWsMessage("Navigation started!");
      } else {
        setWsMessage("Not connected — check if the backend is running.");
      }
    }, []); 

    const wsColor = {
      connected: "bg-emerald-400",
      connecting: "bg-yellow-400 animate-pulse",
      disconnected: "bg-white/20",
      error: "bg-rose-400",
    }[wsStatus];
    const wsLabel = {
      connected: "Robot connected",
      connecting: "Connecting...",
      disconnected: "Disconnected",
      error: "Connection error",
    }[wsStatus];

    return (
      <div className="flex flex-col h-screen overflow-hidden" style={{ background: "#0F0F12", fontFamily: "'Fira Sans', sans-serif" }}>
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
            <StatPill label="Sent" value={stats.sent} />
            <StatPill label="Skipped" value={stats.skipped} />
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

        <div className="flex flex-1 overflow-hidden">
          <Sidebar
            activeView={activeView}
            activeModel={activeModel}
            onViewChange={setActiveView}
            onModelChange={handleModelChange}
            onLogout={() => setShowLogoutModal(true)}
          />

          <main className="flex-1 flex flex-col overflow-y-auto px-6 py-5 gap-5 min-w-0 bg-[#0F0F12] scrollbar-dark">
            <div className="flex items-center justify-between">
              <h1 className="text-sm font-semibold text-white/60">
                Session <span className="font-mono text-blue-400">#0042</span>
                <span className="text-white/20 mx-2">·</span>Mars Exploration A
              </h1>
            </div>

            {activeView === "rewards" && <RewardHistoryView rewardData={rewardData} />}

            {activeView === "gallery" && (
              <GalleryView
                galleryLoading={galleryLoading}
                galleryImages={galleryImages}
                onSelect={setSelectedImage}
              />
            )}

            {activeView === "logs" && <LogsView />}

            {activeView === "live" && (
              <LiveFeedView
                wsStatus={wsStatus}
                wsMessage={wsMessage}
                capturedImageSrc={capturedImageSrc}
                frameNumber={frameNumber}
                receivedAgo={receivedAgo}
                stateVector={stateVector}
                actionTaken={actionTaken}
                uploadStatus={uploadStatus}
                saveTarget={saveTarget}
                user={user}
                captureMode={captureMode}
                currentCaptureMode={currentCaptureMode}
                datasetSavedCount={datasetSavedCount}
                currentPipelineWouldSend={currentPipelineWouldSend}
                onCapture={handleCaptureImage}
                onCaptureModeChange={setCaptureMode}
                onAction={sendAction}
                navigationStarted={navigationStarted}
                onStartNavigation={handleStartNavigation}
              />
            )}
          </main>

          <RightPanel history={history} rewardData={rewardData} />
        </div>

        {selectedImage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-6"
            onClick={() => setSelectedImage(null)}
          >
            <img
              src={selectedImage}
              alt="Full size"
              className="max-w-full max-h-full rounded-xl border border-white/10 object-contain shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white/60 hover:text-white hover:bg-white/20 transition-colors text-sm cursor-pointer"
            >
              ×
            </button>
          </div>
        )}

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
                  onClick={() => {
                    handleLogout();
                    setShowLogoutModal(false);
                  }}
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
