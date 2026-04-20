"use client";

import RewardChart from "./RewardChart";

interface Props {
  rewardData: { step: string; reward: number }[];
}

export default function RewardHistoryView({ rewardData }: Props) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
        <span className="text-[10px] font-semibold text-white/25 tracking-widest uppercase">Reward History</span>
        <span className="font-mono text-[11px] text-white/30">{rewardData.length} steps</span>
      </div>
      <div className="p-5 flex flex-col gap-3">
        <RewardChart data={rewardData} height={192} cellOpacityRange={[0.2, 0.8]} barRadius={3} />
        <div className="flex justify-between">
          <span className="font-mono text-[9px] text-white/15">earliest</span>
          <span className="font-mono text-[9px] text-white/15">latest</span>
        </div>
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
  );
}
