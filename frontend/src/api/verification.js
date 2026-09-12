/**
 * @file Verification + dashboard API calls (aligned with backend routes).
 */
import client from "./client";

/**
 * Submit a quantum signature for full 6-layer verification.
 * @param {string} signature - Signature payload.
 * @param {string} sessionId - Client session id.
 * @param {object} [channelSnapshot] - Optional layer flags (e.g. attack context).
 * @returns {Promise<object>} VerificationResponse payload.
 */
export async function verifySignature(signature, sessionId, channelSnapshot) {
  const { data } = await client.post("/verify", {
    signature,
    session_id: sessionId,
    channel_snapshot: channelSnapshot || null,
  });
  return data;
}

/**
 * Fetch recent verification results, newest first.
 * @param {number} [limit] - Maximum entries.
 * @returns {Promise<Array<object>>} VerificationResponse list.
 */
export async function getVerificationHistory(limit = 20) {
  const { data } = await client.get("/verify/history", { params: { limit } });
  return data;
}

/**
 * Fetch the aggregated dashboard state (trust score, layer verdicts, alerts).
 * @returns {Promise<object>} DashboardSnapshot payload.
 */
export async function getDashboardState() {
  const { data } = await client.get("/dashboard/state");
  return data;
}

/**
 * Fetch a metric time-series for the trend charts.
 * @param {string} metric - "trust_score" | "hom_visibility" | "channel_fidelity".
 * @param {number} [limit] - Maximum points.
 * @returns {Promise<{metric: string, points: Array<object>}>} Series payload.
 */
export async function getMetricHistory(metric, limit = 50) {
  const { data } = await client.get("/dashboard/metrics", { params: { metric, limit } });
  return data;
}

/**
 * Fetch the NHGS lattice eigenvalue spectrum for the spectrum chart.
 * @param {number} [tampering] - Demo tampering intensity in [0, 1].
 * @returns {Promise<{spectrum: number[][], baseline: number[][], exceptional_points: number[][]}>} Spectrum payload.
 */
export async function getNhSpectrum(tampering = 0) {
  const { data } = await client.get("/dashboard/nh-spectrum", { params: { tampering } });
  return data;
}
