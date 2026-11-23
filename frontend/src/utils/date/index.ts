/**
 * Utility functions for consistent date formatting across the platform.
 * Standard format: DD-MM-YYYY (or DD-MM-YYYY HH:mm:ss for timestamps)
 */

export function formatDisplayDate(dateVal?: unknown): string {
  if (dateVal === null || dateVal === undefined || dateVal === '') return 'N/A';
  const str = String(dateVal).trim();
  if (!str || str === 'N/A' || str === 'null' || str === 'undefined') return 'N/A';

  // Direct match for YYYY-MM-DD (e.g. 2026-08-05 or 2026-08-05T...)
  const ymdMatch = str.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (ymdMatch) {
    const [, year, month, day] = ymdMatch;
    return `${day}-${month}-${year}`;
  }

  // Parse ISO date or other date string
  try {
    const d = new Date(str);
    if (isNaN(d.getTime())) return str;
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return str;
  }
}

export function formatDisplayDateTime(dateVal?: unknown, includeSeconds = false): string {
  if (dateVal === null || dateVal === undefined || dateVal === '') return 'N/A';
  const str = String(dateVal).trim();
  if (!str || str === 'N/A' || str === 'null' || str === 'undefined') return 'N/A';

  try {
    const d = new Date(str);
    if (isNaN(d.getTime())) {
      return formatDisplayDate(str);
    }
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');

    if (includeSeconds) {
      const seconds = String(d.getSeconds()).padStart(2, '0');
      return `${day}-${month}-${year} ${hours}:${minutes}:${seconds}`;
    }
    return `${day}-${month}-${year} ${hours}:${minutes}`;
  } catch {
    return str;
  }
}
