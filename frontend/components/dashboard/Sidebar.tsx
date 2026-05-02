"use client";

import { NavView, RLModel } from "@/types/dashboard";
import { MonitorIcon, GridIcon, TrendingUpIcon, ClockIcon, LogOutIcon } from "./icons";

const NAV_ITEMS: { id: NavView; label: string; Icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: "live",    label: "Live feed",      Icon: MonitorIcon },
  { id: "gallery", label: "Image gallery",  Icon: GridIcon },
  { id: "rewards", label: "Reward history", Icon: TrendingUpIcon },
  { id: "logs",    label: "Session logs",   Icon: ClockIcon },
];

const RL_MODELS: { id: RLModel; name: string; sub: string }[] = [
  { id: "random",                name: "Random",                sub: "Baseline · no learning" },
  { id: "deep_contextual_bandit",name: "Deep Contextual Bandit",sub: "DCB · neural network" },
  { id: "contextual_bandit",     name: "Contextual Bandit",     sub: "CB · sample efficient" },
  { id: "sarsa",                 name: "Deep SARSA",            sub: "SARSA · on-policy" },
  { id: "dqn",                   name: "Deep Q-Network",        sub: "DQN · off-policy" },
  { id: "ppo",                   name: "Proximal Policy Opt.",  sub: "PPO · policy gradient" },
  { id: "reinforce",             name: "REINFORCE",             sub: "PG · Monte Carlo" },
  { id: "aac",                   name: "Advantage Actor-Critic",sub: "AAC · actor-critic" },
  { id: "tiny_sac",              name: "Tiny SAC ⚠",            sub: "SAC · not yet trained" },
];

interface Props {
  activeView: NavView;
  activeModel: RLModel;
  onViewChange: (view: NavView) => void;
  onModelChange: (model: RLModel) => void;
  onLogout: () => void;
}

export default function Sidebar({ activeView, activeModel, onViewChange, onModelChange, onLogout }: Props) {
  return (
    <aside className="w-52 shrink-0 flex flex-col border-r border-white/[0.06] bg-[#0D0D10]/50">
      <div className="flex-1 px-3 py-4">
        <p className="text-[9px] font-semibold text-white tracking-[0.2em] uppercase px-2 mb-2">Views</p>
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => onViewChange(id)}
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs transition-colors duration-150 cursor-pointer w-full text-left ${
                activeView === id
                  ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                  : "text-white hover:text-white hover:bg-white/[0.04] border border-transparent"
              }`}
            >
              <Icon size={14} />{label}
            </button>
          ))}
        </nav>
      </div>

      <div className="px-3 py-4 border-t border-white/[0.06]">
        <p className="text-[9px] font-semibold text-white tracking-[0.2em] uppercase px-2 mb-2">RL Model</p>
        <div className="flex flex-col gap-1.5">
          {RL_MODELS.map(({ id, name, sub }) => (
            <button
              key={id}
              onClick={() => onModelChange(id)}
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-md transition-all duration-150 cursor-pointer text-left w-full border ${
                activeModel === id
                  ? "bg-blue-500/10 border-blue-500/25 text-blue-400"
                  : "border-transparent text-white hover:text-white hover:bg-white/[0.03]"
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
          onClick={onLogout}
          className="flex items-center gap-2 px-2.5 py-2 mt-3 w-full rounded-md text-white hover:text-rose-400/70 hover:bg-rose-500/[0.05] transition-colors duration-150 cursor-pointer text-xs"
        >
          <LogOutIcon size={13} />Sign out
        </button>
      </div>
    </aside>
  );
}
