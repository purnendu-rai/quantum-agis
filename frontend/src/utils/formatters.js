/**
 * @file Display formatting helpers for dashboard values.
 */

/**
 * Format a 0-1 trust score as a percentage with one decimal.
 * @param {number} score - Trust score in [0, 1].
 * @returns {string} E.g. "98.4%".
 */
export function formatTrustScore(score) {
  return `${(score * 100).toFixed(1)}%`;
}

/**
 * Format a timestamp as a locale-independent 24-hour HH:MM:SS string.
 * @param {string|number|Date} ts - Parseable timestamp.
 * @returns {string} E.g. "10:32:15".
 */
export function formatTimestamp(ts) {
  const date = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

/**
 * Format a latency in milliseconds with one decimal.
 * @param {number} ms - Latency in ms.
 * @returns {string} E.g. "8.4 ms".
 */
export function formatLatency(ms) {
  return `${ms.toFixed(1)} ms`;
}

/**
 * Format a deviation score with three decimals.
 * @param {number} d - Deviation in [0, 1].
 * @returns {string} E.g. "0.024".
 */
export function formatDeviation(d) {
  return d.toFixed(3);
}

/**
 * Map a verdict string to a Badge tone.
 * @param {string} verdict - "authentic" | "suspicious" | "rejected".
 * @returns {"green"|"amber"|"red"|"gray"} Badge tone key.
 */
export function verdictTone(verdict) {
  return { authentic: 'green', suspicious: 'amber', rejected: 'red' }[verdict] ?? 'gray';
}
