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

export const SEED_HISTORY: HistoryEntry[] = [];

export const SEED_REWARD_HISTORY: { step: string; reward: number }[] = [];
