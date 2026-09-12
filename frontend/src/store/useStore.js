import { create } from 'zustand';

/**
 * @file Global Zustand store: layer statuses, trust score, event feed,
 * metrics, and WebSocket connection state.
 */
export const useStore = create((set) => ({
  // Demo session identity sent with verification/attack requests.
  sessionId: 'demo-session-001',
  // Status of each of the 6 layers, index-aligned with LAYER_NAMES.
  layerStatuses: Array(6).fill('pending'),
  trustScore: 0,
  recentEvents: [],
  metrics: {},
  // Live WebSocket connection state (mirrored in the Header badge).
  wsConnected: false,

  /**
   * Update the status of one layer.
   * @param {number} index - Layer index (0-5).
   * @param {string} status - New status (e.g. "PASS" | "FAIL" | "SUSPICIOUS").
   */
  setLayerStatus: (index, status) =>
    set((state) => ({
      layerStatuses: state.layerStatuses.map((s, i) => (i === index ? status : s)),
    })),

  /**
   * Replace the whole layer-status array (from a dashboard_update frame).
   * @param {Array<string|object>} statuses - Statuses in layer order; entries
   *   may be plain strings or {status} objects.
   */
  setLayerStatuses: (statuses) =>
    set({
      layerStatuses: Array.from({ length: 6 }, (_, index) => {
        const entry = statuses?.[index];
        if (typeof entry === 'string') return entry;
        return entry?.status ?? 'pending';
      }),
    }),

  /**
   * Set the current aggregate trust score.
   * @param {number} score - Trust score in [0, 1].
   */
  setTrustScore: (score) => set({ trustScore: score }),

  /**
   * Prepend a security event to the feed, de-duplicated by timestamp+source
   * (capped at 100 entries).
   * @param {object} event - Event payload.
   */
  addEvent: (event) =>
    set((state) => {
      const key = `${event.timestamp}|${event.source}|${event.message ?? ''}`;
      if (state.recentEvents.some((e) => `${e.timestamp}|${e.source}|${e.message ?? ''}` === key)) {
        return state;
      }
      return { recentEvents: [event, ...state.recentEvents].slice(0, 100) };
    }),

  /**
   * Replace the event feed wholesale (from a dashboard_update frame).
   * @param {Array<object>} events - Server-side event list, newest first.
   */
  setEvents: (events) => set({ recentEvents: Array.isArray(events) ? events.slice(0, 100) : [] }),

  /**
   * Replace the live metrics object.
   * @param {object} metrics - Metric payload from the API/WebSocket.
   */
  setMetrics: (metrics) => set({ metrics }),

  /**
   * Update the WebSocket connection flag shown in the Header.
   * @param {boolean} connected - Whether the live stream is open.
   */
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));

export default useStore;
