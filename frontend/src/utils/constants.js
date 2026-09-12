/**
 * @file Frontend constants: API endpoints, layer metadata, attack catalog.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export const LAYER_NAMES = ["QGM", "HIS", "NHGS", "TCP", "MVS", "BTFE"];
export const LAYER_FULL_NAMES = [
  "Genome Mapping", "HOM Interferometry", "Ghost Sensor",
  "Temporal Coherence", "MDI-QDS Shield", "Bayesian Fusion"
];

export const ATTACK_TYPES = ["forgery", "impersonation", "replay", "channel_tampering", "coherent"];

export const COLORS = {
  quantumBlue: "#00d4ff",
  quantumPurple: "#6a0dad",
  darkBg: "#0a0e27",
  layerBlue: "#0055ff",
  layerCyan: "#00ccff",
  layerOrange: "#ffaa00",
  layerPurple: "#aa44ff",
  layerRed: "#ff2244",
  layerGold: "#ffcc00"
};

/** Security layer metadata shown across the dashboard. */
export const LAYERS = [
  { id: 0, code: "QGM", name: "Quantum Gate Marker" },
  { id: 1, code: "HIS", name: "Holographic Identity Seal" },
  { id: 2, code: "NHGS", name: "Non-Hermitian Gate Shield" },
  { id: 3, code: "TCP", name: "Teleportation Checkpoint" },
  { id: 4, code: "MVS", name: "Multi-Vector Signature" },
  { id: 5, code: "BTFE", name: "Bayesian Threat Fusion Engine" },
];

/** Attack catalogue rendered by the AttackPanel. */
export const ATTACK_TYPE_LABELS = [
  { id: "forgery", label: "Forgery" },
  { id: "impersonation", label: "Impersonation" },
  { id: "replay", label: "Replay" },
  { id: "channel_tampering", label: "Channel Tampering" },
  { id: "coherent", label: "Coherent" },
];

/** Polling/streaming intervals (ms). */
export const REFRESH_INTERVAL_MS = 5000;
