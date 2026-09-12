/**
 * @file Security event log API calls.
 */
import client from "./client";

/**
 * Fetch recent security events, newest first.
 * @param {object} [options] - Query options.
 * @param {number} [options.limit] - Maximum events (1-1000).
 * @param {string} [options.severity] - Optional severity filter (info|warning|critical).
 * @returns {Promise<Array<object>>} SecurityEvent list.
 */
export async function getSecurityEvents({ limit = 100, severity } = {}) {
  const { data } = await client.get("/logs", { params: { limit, severity } });
  return data;
}

/**
 * Export the full event log for SIEM hand-off / demo reports.
 * @returns {Promise<object>} Export payload.
 */
export async function exportLogs() {
  const { data } = await client.get("/logs/export");
  return data;
}
