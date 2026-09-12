import { useEffect, useRef, useState } from 'react';
import { createWebSocket } from '../api/websocket';
import useStore from '../store/useStore';

/**
 * Subscribes to the backend /ws/live stream with exponential-backoff
 * reconnect (1s, 2s, 4s, 8s … 30s max) and dispatches frames to the Zustand
 * store by message type:
 *
 * - ``dashboard_update`` — replaces layer statuses, trust score, recent
 *   events, and metrics.
 * - ``new_event`` — prepends one security event to the feed.
 * - ``attack_detected`` — prepends an attack alert and updates the trust
 *   score.
 *
 * Mount ONCE (in App) so a single connection serves the whole app.
 * @returns {{isConnected: boolean, lastMessage: object|null}} Connection state
 *   and the most recent raw frame.
 */
export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const setWsConnected = useStore((state) => state.setWsConnected);
  const setLayerStatuses = useStore((state) => state.setLayerStatuses);
  const setTrustScore = useStore((state) => state.setTrustScore);
  const setMetrics = useStore((state) => state.setMetrics);
  const setEvents = useStore((state) => state.setEvents);
  const addEvent = useStore((state) => state.addEvent);
  const handlers = useRef(null);

  handlers.current = {
    setWsConnected,
    setLayerStatuses,
    setTrustScore,
    setMetrics,
    setEvents,
    addEvent,
  };

  useEffect(() => {
    const connection = createWebSocket({
      onOpen: () => {
        setIsConnected(true);
        handlers.current.setWsConnected(true);
      },
      onClose: () => {
        setIsConnected(false);
        handlers.current.setWsConnected(false);
      },
      onMessage: (message) => {
        let frame;
        try {
          frame = JSON.parse(message.data);
        } catch {
          return; // ignore malformed frames
        }
        setLastMessage(frame);
        const { type, data } = frame;
        switch (type) {
          case 'dashboard_update': {
            if (Array.isArray(data.layer_statuses)) {
              handlers.current.setLayerStatuses(data.layer_statuses);
            }
            if (typeof data.trust_score === 'number') {
              handlers.current.setTrustScore(data.trust_score);
            }
            if (Array.isArray(data.recent_events)) {
              handlers.current.setEvents(data.recent_events);
            }
            if (data.metrics) {
              handlers.current.setMetrics(data.metrics);
            }
            break;
          }
          case 'new_event': {
            if (data && Object.keys(data).length) {
              handlers.current.addEvent(data);
            }
            break;
          }
          case 'attack_detected': {
            handlers.current.addEvent({
              timestamp: new Date().toISOString(),
              severity: data.detected ? 'warning' : 'critical',
              source: `attack.${data.attack_type}`,
              message: `Attack ${data.attack_type} ${data.detected ? 'DETECTED' : 'BYPASSED'} | trust=${(
                data.trust_score_after ?? 0
              ).toFixed(3)} | decision=${data.decision ?? 'unknown'}`,
              decision: data.decision,
              trust_score: data.trust_score_after,
            });
            if (typeof data.trust_score_after === 'number') {
              handlers.current.setTrustScore(data.trust_score_after);
            }
            break;
          }
          default:
            break; // unknown frame types are ignored for forward compatibility
        }
      },
    });
    return () => connection.close();
  }, []);

  return { isConnected, lastMessage };
}

export default useWebSocket;
