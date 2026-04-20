"use client";

import { ClockIcon } from "./icons";

interface LogEntry {
  id: number;
  timestamp: string;
  level: "info" | "warn" | "error";
  message: string;
}

interface Props {
  logs?: LogEntry[];
}

const PLACEHOLDER_LOGS: LogEntry[] = [
  { id: 1, timestamp: "12:04:31", level: "info",  message: "WebSocket connection established" },
  { id: 2, timestamp: "12:04:28", level: "info",  message: "Model switched to: random" },
  { id: 3, timestamp: "12:04:24", level: "info",  message: "Image captured — decision: send" },
  { id: 4, timestamp: "12:04:19", level: "warn",  message: "Image rejected: too similar to previous frame" },
  { id: 5, timestamp: "12:04:10", level: "info",  message: "Reward received for image 20240418_120410" },
  { id: 6, timestamp: "12:04:01", level: "error", message: "Capture failed: camera not ready" },
];

const LEVEL_STYLE: Record<LogEntry["level"], string> = {
  info:  "text-white/40",
  warn:  "text-yellow-400/70",
  error: "text-rose-400/80",
};

const LEVEL_DOT: Record<LogEntry["level"], string> = {
  info:  "bg-white/20",
  warn:  "bg-yellow-400",
  error: "bg-rose-400",
};

export default function LogsView({ logs = PLACEHOLDER_LOGS }: Props) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
        <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">Session Logs</span>
        <span className="font-mono text-[11px] text-white/30">{logs.length} entries</span>
      </div>

      {logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 gap-3">
          <ClockIcon size={22} className="text-white/10" />
          <p className="text-[11px] text-white/25">No log entries yet.</p>
        </div>
      ) : (
        <div className="p-4 flex flex-col gap-1 font-mono text-[11px]">
          {logs.map((entry) => (
            <div key={entry.id} className="flex items-start gap-3 py-1.5 border-b border-white/[0.03] last:border-0">
              <span className="text-white/25 shrink-0 w-16">{entry.timestamp}</span>
              <span className={`shrink-0 flex items-center gap-1.5 w-12 ${LEVEL_STYLE[entry.level]}`}>
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${LEVEL_DOT[entry.level]}`} />
                {entry.level}
              </span>
              <span className="text-white/50 break-all">{entry.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
