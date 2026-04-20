"use client";

import { HistoryEntry } from "@/types/dashboard";
import { ImageIcon } from "./icons";
import RewardChart from "./RewardChart";

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

interface Props {
  history: HistoryEntry[];
  rewardData: { step: string; reward: number }[];
}

export default function RightPanel({ history, rewardData }: Props) {
  return (
    <aside className="w-64 shrink-0 flex flex-col border-l border-white/[0.06] bg-[#0D0D10]/50">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
        <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">History</span>
        <span className="font-mono text-[11px] text-white/30">{history.length} frames</span>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {history.map((entry) => (
          <HistoryRow key={entry.id} entry={entry} />
        ))}
      </div>

      <div className="border-t border-white/[0.06] px-4 py-4 shrink-0">
        <p className="text-[10px] font-semibold text-white/20 tracking-widest uppercase mb-3">Cumulative Reward</p>
        <RewardChart data={rewardData} height={64} cellOpacityRange={[0.2, 0.5]} barRadius={2} />
        <div className="flex justify-between mt-1">
          <span className="font-mono text-[9px] text-white/15">early</span>
          <span className="font-mono text-[9px] text-white/15">now</span>
        </div>
      </div>
    </aside>
  );
}
