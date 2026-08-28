/** Unit tests for the appointment date helpers. */
import { describe, expect, it } from 'vitest';

import { formatDate, formatTime, isClosedDay, maxBookableIso, toIsoDate, todayIso } from './dateUtils';

describe('toIsoDate', () => {
  it('formats a date as YYYY-MM-DD', () => {
    expect(toIsoDate(new Date(2026, 7, 24))).toBe('2026-08-24');
  });

  it('pads single digit months and days', () => {
    expect(toIsoDate(new Date(2026, 0, 5))).toBe('2026-01-05');
  });
});

describe('isClosedDay', () => {
  it('reports Friday as closed', () => {
    expect(isClosedDay('2026-08-28')).toBe(true);
  });

  it('reports a Monday as open', () => {
    expect(isClosedDay('2026-08-24')).toBe(false);
  });

  it('treats an empty value as not closed', () => {
    expect(isClosedDay('')).toBe(false);
  });
});

describe('maxBookableIso', () => {
  it('is later than today', () => {
    expect(maxBookableIso() > todayIso()).toBe(true);
  });
});

describe('formatTime', () => {
  it('shortens HH:MM:SS to HH:MM', () => {
    expect(formatTime('10:00:00')).toBe('10:00');
  });

  it('returns an empty string for a missing value', () => {
    expect(formatTime(undefined)).toBe('');
  });
});

describe('formatDate', () => {
  it('produces a readable date', () => {
    expect(formatDate('2026-08-24')).toContain('2026');
  });
});
