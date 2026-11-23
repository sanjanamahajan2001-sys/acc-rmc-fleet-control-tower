import { describe, it, expect } from 'vitest';
import { formatDisplayDate, formatDisplayDateTime } from '../utils/date';

describe('Standardized Date Formatting Utilities (DD-MM-YYYY)', () => {
  it('formats YYYY-MM-DD into DD-MM-YYYY', () => {
    expect(formatDisplayDate('2026-08-05')).toBe('05-08-2026');
    expect(formatDisplayDate('2026-03-01')).toBe('01-03-2026');
    expect(formatDisplayDate('2025-12-31')).toBe('31-12-2025');
  });

  it('formats ISO timestamps into DD-MM-YYYY', () => {
    expect(formatDisplayDate('2026-08-05T14:30:00Z')).toBe('05-08-2026');
    expect(formatDisplayDate('2026-03-01T08:00:00.000Z')).toBe('01-03-2026');
  });

  it('handles null, undefined, empty, and invalid values gracefully', () => {
    expect(formatDisplayDate(null)).toBe('N/A');
    expect(formatDisplayDate(undefined)).toBe('N/A');
    expect(formatDisplayDate('')).toBe('N/A');
    expect(formatDisplayDate('   ')).toBe('N/A');
  });

  it('formats ISO timestamps with time as DD-MM-YYYY HH:mm', () => {
    const formatted = formatDisplayDateTime('2026-08-05T14:30:00');
    expect(formatted).toContain('05-08-2026');
    expect(formatted).toContain(':');
  });
});
