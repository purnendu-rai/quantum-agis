/**
 * @file Attack-simulation API calls (aligned with backend routes).
 */
import client from "./client";

/**
 * Execute a simulated attack against the current session.
 * @param {string} attackType - One of the ATTACK_TYPES values.
 * @param {number} intensity - Attack strength in [0, 1].
 * @param {string} sessionId - Target session id.
 * @returns {Promise<object>} AttackResponse payload.
 */
export async function runAttack(attackType, intensity, sessionId) {
  const { data } = await client.post(`/attack/${attackType}`, null, {
    params: { intensity, session_id: sessionId },
  });
  return data;
}

/**
 * List supported attack types and their descriptors.
 * @returns {Promise<Array<object>>} Attack descriptors.
 */
export async function listAttackTypes() {
  const { data } = await client.get("/attack/types");
  return data;
}
