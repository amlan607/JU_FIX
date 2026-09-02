/** Unit tests for the health record display helpers. */
import { describe, expect, it } from 'vitest';

import { RECORD_TYPES, formatVisitDate, recordTypeLabel } from './recordTypes';

describe('recordTypeLabel', () => {
  it('maps a stored value to its display label', () => {
    expect(recordTypeLabel('lab_result')).toBe('Lab Result');
  });

  it('maps every declared option', () => {
    RECORD_TYPES.forEach((type) => {
      expect(recordTypeLabel(type.value)).toBe(type.label);
    });
  });

  it('falls back for an unknown value', () => {
    expect(recordTypeLabel('unknown_value')).toBe('Clinical Note');
  });
});

describe('formatVisitDate', () => {
  it('formats an ISO date for display', () => {
    expect(formatVisitDate('2026-08-24')).toContain('2026');
  });

  it('returns an empty string when the date is missing', () => {
    expect(formatVisitDate('')).toBe('');
  });
});
