/**
 * @file WebSocket factory for the live dashboard event stream.
 * Auto-reconnects with exponential backoff: 1s, 2s, 4s, 8s … capped at 30s.
 */
import { WS_URL } from '../utils/constants';

const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

/**
 * Open a WebSocket to the backend /ws/live endpoint.
 * The connection retries forever with exponential backoff; the delay resets
 * to 1s after every successful open.
 * @param {object} [handlers] - Optional callbacks.
 * @param {() => void} [handlers.onOpen] - Called on every successful open.
 * @param {() => void} [handlers.onClose] - Called on every drop (pre-reconnect).
 * @param {(message: MessageEvent) => void} [handlers.onMessage] - Called per frame.
 * @returns {{close: () => void}} Handle with a close() that stops reconnecting.
 */
export function createWebSocket({ onOpen, onClose, onMessage } = {}) {
  let attempt = 0;
  let stopped = false;
  let socket = null;

  /**
   * Open the socket and wire the retry loop.
   */
  function connect() {
    socket = new WebSocket(`${WS_URL}/ws/live`);
    socket.onopen = () => {
      attempt = 0;
      onOpen?.();
    };
    socket.onmessage = (message) => onMessage?.(message);
    socket.onclose = () => {
      if (stopped) return;
      onClose?.();
      const delay = Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
      attempt += 1;
      setTimeout(() => {
        if (!stopped) connect();
      }, delay);
    };
  }

  connect();
  return {
    /** Close the socket and cancel future reconnects. */
    close: () => {
      stopped = true;
      socket?.close();
    },
  };
}
