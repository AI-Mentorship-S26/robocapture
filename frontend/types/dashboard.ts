export type NavView = "live" | "gallery" | "rewards" | "logs";
export type RLModel =
  | "random"
  | "deep_contextual_bandit"
  | "contextual_bandit"
  | "sarsa"
  | "dqn"
  | "ppo"
  | "reinforce"
  | "aac"
  | "tiny_sac";
export type FrameAction = "+R" | "-P" | null;
export type WsStatus = "connecting" | "connected" | "disconnected" | "error";

export interface GalleryImage {
  name: string;
  url: string;
  model: string;
  capturedAt: string;
}

export interface HistoryEntry {
  id: number;
  timestamp: string;
  status: "sent" | "skipped";
  action: FrameAction;
}

export interface StateVector {
  entropy: number;
  edgeDensity: number;
  novelty: number;
  opticalFlow: number;
}

export const SEED_HISTORY: HistoryEntry[] = [
  { id: 1, timestamp: "12:04:31", status: "sent",    action: "+R" },
  { id: 2, timestamp: "12:04:28", status: "skipped", action: null },
  { id: 3, timestamp: "12:04:24", status: "sent",    action: "-P" },
  { id: 4, timestamp: "12:04:19", status: "sent",    action: "+R" },
  { id: 5, timestamp: "12:04:15", status: "skipped", action: null },
  { id: 6, timestamp: "12:04:10", status: "sent",    action: "+R" },
  { id: 7, timestamp: "12:04:06", status: "sent",    action: "+R" },
  { id: 8, timestamp: "12:04:01", status: "skipped", action: null },
];

export const SEED_REWARD_HISTORY = [
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
