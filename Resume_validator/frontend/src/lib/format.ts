// Shared formatting + parsing helpers. Several ApplicationRead fields
// (score_breakdown, matched_skills, missing_skills, strengths, gaps,
// responsibilities_matched, responsibilities_missing, experience_result)
// are JSON-encoded strings on the backend model, not real arrays/objects.
// Always go through asList()/asRecord() rather than assuming the shape.

/** Score thresholds mirrored from ats_agent.config (SELECT_CUTOFF / REJECT_FLOOR). */
export const SELECT_CUTOFF = 70;
export const REJECT_FLOOR = 35;

/**
 * Parse a field that may be a JSON-encoded array, an already-parsed array,
 * a comma-separated plain string, or empty/null. Never throws.
 */
export function asList(value: unknown): string[] {
  if (value == null) return [];
  if (Array.isArray(value)) return value.map(String);
  if (typeof value !== 'string') return [];
  const trimmed = value.trim();
  if (!trimmed) return [];
  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) return parsed.map(String);
    // A JSON object is a grouped structure, never a list of labels — returning
    // its keys is what once leaked "skills / keywords / responsibilities" into
    // the UI. Use parseEvidenceGroups() for grouped data.
    if (parsed && typeof parsed === 'object') return [];
    return [String(parsed)];
  } catch {
    // Not JSON — treat as a plain comma-separated string.
    return trimmed
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
}

/**
 * Parse a field that may be a JSON-encoded object, an already-parsed
 * object, or empty/null. Never throws.
 */
export function asRecord(value: unknown): Record<string, unknown> {
  if (value == null) return {};
  if (typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value !== 'string') return {};
  const trimmed = value.trim();
  if (!trimmed) return {};
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    return {};
  } catch {
    return {};
  }
}

/** Round a raw score to a display-friendly whole number, or an em dash if absent. */
export function formatScore(score: number | null | undefined): string {
  if (score == null || Number.isNaN(score)) return '—';
  return Math.round(score).toString();
}

/** Which status color a score should use, aligned to the backend's own cutoffs. */
export function scoreTone(score: number | null | undefined): 'success' | 'warning' | 'danger' | 'neutral' {
  if (score == null || Number.isNaN(score)) return 'neutral';
  if (score >= SELECT_CUTOFF) return 'success';
  if (score < REJECT_FLOOR) return 'danger';
  return 'warning';
}

/** Initials for an avatar chip, e.g. "Priya Nair" -> "PN". */
export function initials(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** e.g. "Mar 14, 2026" */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

/** e.g. "Mar 14, 2026 · 2:30 PM" */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  const date = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `${date} \u00B7 ${time}`;
}

/** e.g. "2:30 PM" from an ISO datetime or an "HH:MM:SS" time-only string. */
export function formatTime(value: string | null | undefined): string {
  if (!value) return '—';
  if (/^\d{2}:\d{2}(:\d{2})?$/.test(value)) {
    const [h, m] = value.split(':').map(Number);
    const d = new Date();
    d.setHours(h, m, 0, 0);
    return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  }
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

/** "needs_review" / "NEEDS_REVIEW" -> "Needs review" */
export function humanize(value: string | null | undefined): string {
  if (!value) return '—';
  const spaced = value.replace(/[_-]+/g, ' ').trim().toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function truncate(value: string, max = 140): string {
  if (value.length <= max) return value;
  return value.slice(0, max - 1).trimEnd() + '\u2026';
}

// ------------------------------------------------------------------
// Grouped evidence (strengths / gaps)
// ------------------------------------------------------------------

export interface EvidenceGroups {
  skills: string[];
  keywords: string[];
  responsibilities: string[];
  /** Plain-list fallback for records that stored a flat array of strings. */
  other: string[];
}

/**
 * `strengths` and `gaps` are stored as a JSON object shaped
 * { skills: [...], keywords: [...], responsibilities: [...] }. This turns
 * either that shape (or an older flat list) into typed groups so screens
 * never have to touch raw keys.
 */
export function parseEvidenceGroups(value: unknown): EvidenceGroups {
  const empty: EvidenceGroups = { skills: [], keywords: [], responsibilities: [], other: [] };
  if (value == null) return empty;

  let parsed: unknown = value;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return empty;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      return { ...empty, other: asList(trimmed) };
    }
  }

  if (Array.isArray(parsed)) return { ...empty, other: parsed.map(String) };
  if (parsed && typeof parsed === 'object') {
    const obj = parsed as Record<string, unknown>;
    return {
      skills: asList(obj.skills),
      keywords: asList(obj.keywords),
      responsibilities: asList(obj.responsibilities),
      other: [],
    };
  }
  return empty;
}

// ------------------------------------------------------------------
// Score components
// ------------------------------------------------------------------

/**
 * Each component score is a weighted point value, not a 0-100 percentage.
 * These maxima mirror the scoring weights so bars can show progress toward
 * each component's own ceiling (e.g. Skills 44 / 60).
 */
export const SCORE_WEIGHTS = {
  skills: 60,
  experience: 25,
  responsibilities: 10,
  keywords: 5,
} as const;

export function componentPercent(value: number | null | undefined, max: number): number | null {
  if (value == null || Number.isNaN(value) || max <= 0) return null;
  return Math.max(0, Math.min(100, (value / max) * 100));
}

// ------------------------------------------------------------------
// Terminology
// ------------------------------------------------------------------

/** Recruiter-facing names for the evaluation lifecycle. */
export function evaluationStatusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'Pending':
      return 'Not Evaluated';
    case 'Running':
      return 'Evaluating';
    case 'Completed':
      return 'Completed';
    case 'Failed':
      return 'Failed';
    default:
      return status ? humanize(status) : 'Not Evaluated';
  }
}

/** True when a free-form status field carries real information (not empty / "None"). */
export function hasStatus(value: string | null | undefined): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v !== '' && v !== 'none' && v !== 'null';
}

// ------------------------------------------------------------------
// Experience
// ------------------------------------------------------------------

export interface ExperienceSummary {
  candidate: string;
  required: string;
  label: string;
  tone: 'success' | 'warning' | 'neutral';
}

function years(n: number): string {
  return `${n} ${n === 1 ? 'year' : 'years'}`;
}

export function summarizeExperience(exp: {
  candidate_years?: number | null;
  required_min_years?: number | null;
  required_max_years?: number | null;
  status?: string | null;
  matches_requirement?: boolean | null;
}): ExperienceSummary | null {
  const hasAny =
    exp.candidate_years != null ||
    exp.required_min_years != null ||
    exp.required_max_years != null ||
    Boolean(exp.status);
  if (!hasAny) return null;

  const min = exp.required_min_years;
  const max = exp.required_max_years;
  let required = 'Not specified';
  if (min != null && max != null) required = min === max ? years(min) : `${min}\u2013${max} years`;
  else if (min != null) required = `${min}+ years`;
  else if (max != null) required = `Up to ${years(max)}`;

  let label = 'Not enough information';
  let tone: ExperienceSummary['tone'] = 'neutral';
  switch (exp.status) {
    case 'meets_requirement':
      label = 'Meets requirement';
      tone = 'success';
      break;
    case 'above_range':
      label = 'Above required range';
      tone = 'success';
      break;
    case 'below_minimum':
      label = 'Below minimum';
      tone = 'warning';
      break;
    case 'no_requirement':
      label = 'No experience requirement';
      break;
    case 'unknown':
      break;
    default:
      if (exp.matches_requirement === true) {
        label = 'Meets requirement';
        tone = 'success';
      } else if (exp.matches_requirement === false) {
        label = 'Below requirement';
        tone = 'warning';
      }
  }

  return {
    candidate: exp.candidate_years != null ? years(exp.candidate_years) : 'Not found in resume',
    required,
    label,
    tone,
  };
}
