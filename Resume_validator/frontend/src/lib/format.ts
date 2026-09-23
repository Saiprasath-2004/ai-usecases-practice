// Several Application fields are stored as JSON-encoded strings in the
// backend (e.g. matched_skills: str = "" # JSON). This normalizes whatever
// shape actually arrives (string, already-parsed array/object, null,
// empty string) into something safe to render.

export function asList(value: unknown): string[] {
  if (value == null) return [];
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return [];
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed.map(String);
      if (parsed && typeof parsed === 'object') return Object.values(parsed).map(String);
      return [String(parsed)];
    } catch {
      return [trimmed];
    }
  }
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).map(String);
  return [String(value)];
}

export function asRecord(value: unknown): Record<string, unknown> | null {
  if (value == null) return null;
  if (typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
    } catch {
      return null;
    }
  }
  return null;
}

export function scoreTone(score: number | null | undefined): 'high' | 'mid' | 'low' | 'none' {
  if (score == null) return 'none';
  if (score >= 75) return 'high';
  if (score >= 50) return 'mid';
  return 'low';
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return '—';
  return `${Math.round(score)}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
