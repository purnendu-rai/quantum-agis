/**
 * @file Tests for display formatting helpers.
 */
import { describe, expect, it } from 'vitest';
import {
  formatDeviation,
  formatLatency,
  formatTimestamp,
  formatTrustScore,
  verdictTone,
} from './formatters.js';

describe('formatTrustScore', () => {
  it('renders one-decimal percentages', () => {
    expect(formatTrustScore(0.984)).toBe('98.4%');
  });

  it('rounds beyond one decimal', () => {
    expect(formatTrustScore(0.998906)).toBe('99.9%');
  });

  it('handles zero', () => {
    expect(formatTrustScore(0)).toBe('0.0%');
  });
});

describe('formatTimestamp', () => {
  it('renders locale-independent 24-hour time', () => {
    expect(formatTimestamp('2026-09-12T10:32:15Z')).toMatch(/^\d{2}:\d{2}:\d{2}$/);
  });

  it('pads single-digit components', () => {
    const value = formatTimestamp(new Date(2026, 0, 1, 3, 5, 7).getTime());
    expect(value).toBe('03:05:07');
  });
});

describe('formatLatency', () => {
  it('renders one-decimal milliseconds', () => {
    expect(formatLatency(8.44)).toBe('8.4 ms');
  });
});

describe('formatDeviation', () => {
  it('renders three-decimal deviations', () => {
    expect(formatDeviation(0.0244)).toBe('0.024');
  });
});

describe('verdictTone', () => {
  it('maps verdicts to badge tones', () => {
    expect(verdictTone('authentic')).toBe('green');
    expect(verdictTone('suspicious')).toBe('amber');
    expect(verdictTone('rejected')).toBe('red');
  });

  it('falls back to gray for unknown verdicts', () => {
    expect(verdictTone('whatever')).toBe('gray');
  });
});
