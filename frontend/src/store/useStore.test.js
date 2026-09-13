/**
 * @file Tests for the global Zustand store.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { useStore } from './useStore.js';

describe('useStore', () => {
  beforeEach(() => {
    // Reset the slices the tests touch.
    useStore.setState({
      layerStatuses: Array(6).fill('pending'),
      trustScore: 0,
      recentEvents: [],
      metrics: {},
      wsConnected: false,
    });
  });

  it('starts with six pending layer statuses', () => {
    expect(useStore.getState().layerStatuses).toEqual([
      'pending', 'pending', 'pending', 'pending', 'pending', 'pending',
    ]);
  });

  it('setLayerStatus updates only the targeted index', () => {
    useStore.getState().setLayerStatus(2, 'FAIL');
    const statuses = useStore.getState().layerStatuses;
    expect(statuses[2]).toBe('FAIL');
    expect(statuses[1]).toBe('pending');
    expect(statuses[3]).toBe('pending');
  });

  it('setLayerStatuses accepts objects and strings', () => {
    useStore.getState().setLayerStatuses([{ status: 'PASS' }, 'FAIL']);
    expect(useStore.getState().layerStatuses[0]).toBe('PASS');
    expect(useStore.getState().layerStatuses[1]).toBe('FAIL');
  });

  it('setTrustScore stores the live value', () => {
    useStore.getState().setTrustScore(0.4615);
    expect(useStore.getState().trustScore).toBeCloseTo(0.4615);
  });

  it('addEvent prepends and caps the feed at 100', () => {
    for (let i = 0; i < 120; i++) {
      useStore.getState().addEvent({ timestamp: `t-${i}`, source: 'test', message: `m-${i}` });
    }
    const events = useStore.getState().recentEvents;
    expect(events).toHaveLength(100);
    expect(events[0].message).toBe('m-119');
  });

  it('addEvent de-duplicates identical timestamp+source+message events', () => {
    const event = { timestamp: 't-1', source: 'sim', message: 'same' };
    useStore.getState().addEvent(event);
    useStore.getState().addEvent(event);
    expect(useStore.getState().recentEvents).toHaveLength(1);
  });

  it('setMetrics replaces the metrics object', () => {
    useStore.getState().setMetrics({ hom_visibility: 0.98 });
    expect(useStore.getState().metrics.hom_visibility).toBe(0.98);
  });

  it('setWsConnected mirrors the connection flag', () => {
    useStore.getState().setWsConnected(true);
    expect(useStore.getState().wsConnected).toBe(true);
  });
});
