"use client";

import { StateVector, WsStatus } from "@/types/dashboard";
import { MonitorIcon } from "./icons";

const WS_COLOR: Record<WsStatus, string> = {
  connected: "bg-emerald-400",
  connecting: "bg-yellow-400 animate-pulse",
  disconnected: "bg-white/20",
  error: "bg-rose-400",
};

const WS_LABEL: Record<WsStatus, string> = {
  connected: "Robot connected",
  connecting: "Connecting...",
  disconnected: "Disconnected",
  error: "Connection error",
};

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

interface Props {
  wsStatus: WsStatus;
  wsMessage: string;
  capturedImageSrc: string;
  frameNumber: number;
  receivedAgo: string;
  stateVector: StateVector;
  actionTaken: boolean;
  uploadStatus: "idle" | "uploading" | "saved" | "error";
  saveTarget: "supabase" | "pi_dataset";
  user: { email?: string; id?: string } | null;
  captureMode: "live" | "dataset";
  currentCaptureMode: "live" | "dataset";
  datasetSavedCount: number;
  currentPipelineWouldSend: boolean | null;
  navigationStarted: boolean;
  onStartNavigation: () => void;
  onCapture: () => void;
  onCaptureModeChange: (mode: "live" | "dataset") => void;
  onAction: (action: "+R" | "-P" | "skip") => void;
}

export default function LiveFeedView({
  wsStatus,
  wsMessage,
  capturedImageSrc,
  frameNumber,
  receivedAgo,
  stateVector,
  actionTaken,
  uploadStatus,
  saveTarget,
  user,
  captureMode,
  currentCaptureMode,
  datasetSavedCount,
  currentPipelineWouldSend,
  navigationStarted,
  onStartNavigation,
  onCapture,
  onCaptureModeChange,
  onAction,
}: Props) {
  const wsColor = WS_COLOR[wsStatus];
  const wsLabel = WS_LABEL[wsStatus];
  const loginRequired = captureMode === "live" && !user;
  const feedbackHeading = currentCaptureMode === "dataset" ? "Dataset Labeling" : "Your Feedback";
  const feedbackNote =
    currentCaptureMode === "dataset"
      ? "These labels are saved into the Pi dataset and used later for offline training."
      : "These actions update the active RL model and optionally save to Supabase.";

  const statusCopy =
    saveTarget === "pi_dataset"
      ? {
          uploading: "Saving dataset row on Pi...",
          saved: "Dataset row saved on Pi",
          error: "Dataset save failed - check Pi server",
        }
      : {
          uploading: "Saving to Supabase...",
          saved: "Image saved to Supabase Storage",
          error: "Save failed - check Supabase bucket",
        };

  return (
    <>
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col relative">
        <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
          <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">WebSocket</span>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full border border-white/[0.08] bg-white/[0.04]">
            <span className={`w-1.5 h-1.5 rounded-full ${wsColor}`} />
            <span className="text-[10px] text-white/50">{wsLabel}</span>
          </div>
        </div>

        <div className="p-5 flex flex-col gap-4 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => onCaptureModeChange("live")}
              className={`px-3 py-1.5 rounded-full text-[11px] font-semibold transition-colors ${
                captureMode === "live"
                  ? "bg-blue-500/20 border border-blue-500/40 text-blue-300"
                  : "bg-white/[0.03] border border-white/[0.08] text-white/45 hover:text-white/70"
              }`}
            >
              Live RL
            </button>
            <button
              onClick={() => onCaptureModeChange("dataset")}
              className={`px-3 py-1.5 rounded-full text-[11px] font-semibold transition-colors ${
                captureMode === "dataset"
                  ? "bg-emerald-500/20 border border-emerald-500/40 text-emerald-300"
                  : "bg-white/[0.03] border border-white/[0.08] text-white/45 hover:text-white/70"
              }`}
            >
              Dataset Collection
            </button>
            <span className="font-mono text-[11px] text-white/35 ml-auto">
              Dataset rows <span className="text-white/60">{datasetSavedCount}</span>
            </span>
          </div>

          <div className="p-3 rounded-lg bg-[#161619] border border-white/[0.06] min-h-[48px] flex items-center justify-center">
            <p className="text-[11px] font-mono text-white/40 italic text-center">
              {wsMessage ? `Last message: ${wsMessage}` : "Waiting for backend response..."}
            </p>
          </div>

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

          <div className="flex items-center gap-3 flex-wrap justify-center">
            <span className="font-mono text-[11px] text-white/30">
              Frame <span className="text-white/50">#{frameNumber.toLocaleString()}</span>
              <span className="text-white/20 mx-2">·</span>640x480
            </span>
            <span className="text-[11px] text-white/25">Received {receivedAgo}</span>
            {currentCaptureMode === "dataset" && currentPipelineWouldSend !== null && (
              <span
                className={`text-[11px] px-2 py-1 rounded-full border ${
                  currentPipelineWouldSend
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                }`}
              >
                Pipeline would {currentPipelineWouldSend ? "send" : "reject"}
              </span>
            )}
          </div>

          {captureMode === "live" && (
            <div className="flex gap-3">
              <button
                onClick={onStartNavigation}
                disabled={navigationStarted}
                className="flex-1 py-2.5 rounded-full bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all"
              >
                {navigationStarted ? "Navigation Running..." : "Start Navigation"}
              </button>
              <button
                onClick={onCapture}
                disabled={navigationStarted}
                className="flex-1 py-2.5 rounded-full bg-white text-black text-sm font-semibold hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all"
              >
                Capture Image
              </button>
            </div>
          )}

          {captureMode === "dataset" && (
            <button
              onClick={onCapture}
              className="w-full py-2.5 rounded-full bg-white text-black text-sm font-semibold hover:opacity-80 active:scale-95 transition-all"
            >
              Capture Dataset Image
            </button>
          )}
        </div>

        {loginRequired && (
          <div className="absolute inset-0 rounded-xl bg-[#0F0F12]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3">
            <p className="text-[15px] font-semibold text-white/80">Login required</p>
            <p className="text-[12px] text-white/40 text-center px-6">
              You must be logged in to use the live RL feedback flow.
            </p>
            <a
              href="/login"
              className="mt-1 px-6 py-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all"
            >
              Go to Login
            </a>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5">
        <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-2">{feedbackHeading}</p>
        <p className="text-[11px] text-white/35 mb-4">{feedbackNote}</p>
        <div className="grid grid-cols-3 gap-3">
          <button
            onClick={() => onAction("+R")}
            disabled={!capturedImageSrc || actionTaken}
            className="flex items-center justify-center gap-2 py-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm font-semibold hover:bg-emerald-500/15 hover:border-emerald-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            <span className="text-base font-bold leading-none">+</span>
            Reward
          </button>
          <button
            onClick={() => onAction("-P")}
            disabled={!capturedImageSrc || actionTaken}
            className="flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-400 text-sm font-semibold hover:bg-rose-500/15 hover:border-rose-500/40 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            <span className="text-base font-bold leading-none">-</span>
            Punishment
          </button>
          <button
            onClick={() => onAction("skip")}
            disabled={!capturedImageSrc || actionTaken}
            className="flex items-center justify-center py-3 rounded-xl border border-white/[0.08] bg-white/[0.03] text-white/50 text-sm font-semibold hover:bg-white/[0.07] hover:text-white/70 hover:border-white/15 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            Skip
          </button>
        </div>
      </div>

      {uploadStatus !== "idle" && (
        <div
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-[11px] font-mono ${
            uploadStatus === "uploading"
              ? "border-blue-500/20 bg-blue-500/5 text-blue-400"
              : uploadStatus === "saved"
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                : "border-rose-500/20 bg-rose-500/5 text-rose-400"
          }`}
        >
          {uploadStatus === "uploading" && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
          {uploadStatus === "saved" && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
          {uploadStatus === "error" && <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />}
          {uploadStatus === "uploading"
            ? statusCopy.uploading
            : uploadStatus === "saved"
              ? statusCopy.saved
              : statusCopy.error}
        </div>
      )}

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-5">
        <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-4">
          Frame Features <span className="normal-case text-white/15 ml-1">(State Vector)</span>
        </p>
        <div className="flex flex-col gap-3.5">
          <StateBar label="Entropy" value={stateVector.entropy} color="#3B82F6" />
          <StateBar label="Edge density" value={stateVector.edgeDensity} color="#3B82F6" />
          <StateBar label="Novelty" value={stateVector.novelty} color="#10B981" />
          <StateBar label="Optical flow" value={stateVector.opticalFlow} color="#F59E0B" />
          <div className="flex items-center gap-3 mt-1 pt-3 border-t border-white/[0.04]">
            <span className="text-[11px] text-white/30 w-24 shrink-0">CNN embedding</span>
            <span className="font-mono text-[11px] text-white/20">1280-dim · MobileNetV2</span>
          </div>
        </div>
      </div>
    </>
  );
}
