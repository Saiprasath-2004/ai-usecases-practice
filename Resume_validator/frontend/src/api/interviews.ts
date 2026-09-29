import type { InterviewCreate, InterviewInline, InterviewRead } from '../types';
import { createInterview as createInterviewApi } from './calendar';

/**
 * BACKEND GAP: there is no GET endpoint to list interviews — not by
 * recruiter, not by application, not by date (confirmed against
 * api/routes/calendar.py and api/routes/applications.py; only two POST
 * endpoints ever produce an Interview, and neither response is persisted
 * anywhere the frontend can re-fetch).
 *
 * Every interview this frontend instance creates (via "Schedule Interview"
 * in Human Review, or a manual booking on the Calendar page) is cached here
 * in localStorage, keyed by application id, so it survives a page refresh.
 * This is explicitly a stand-in, not a real list:
 *   - it only knows about interviews booked from THIS browser
 *   - it cannot see interviews booked before this cache existed
 *   - invitation_status / candidate_response are frozen at booking time
 *     unless later refreshed via respondToInterview()'s response
 *
 * When the backend adds GET /calendar/interviews (or similar), delete this
 * file's storage logic and point the Interviews/Calendar pages at the real
 * endpoint instead — the read shape (CachedInterview[]) is deliberately
 * close to InterviewRead so that swap stays small.
 */

const STORAGE_KEY = 'ats_frontend_interview_cache_v1';

export interface CachedInterview {
  applicationId: string;
  candidateEmail: string;
  scheduledAt: string;
  durationMinutes: number;
  status: string;
  provider: string | null;
  meetingUrl: string | null;
  invitationStatus?: string;
  candidateResponse?: string;
  cachedAt: string;
}

function readCache(): Record<string, CachedInterview> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeCache(cache: Record<string, CachedInterview>) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
  } catch {
    // Storage unavailable (private browsing, quota) — degrade silently,
    // the app still works, it just won't remember interviews on refresh.
  }
}

export function listCachedInterviews(): CachedInterview[] {
  return Object.values(readCache()).sort(
    (a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime(),
  );
}

export function getCachedInterview(applicationId: string): CachedInterview | null {
  return readCache()[applicationId] ?? null;
}

export function cacheInterviewFromInline(interview: InterviewInline | InterviewRead) {
  const cache = readCache();
  cache[interview.application_id] = {
    applicationId: interview.application_id,
    candidateEmail: interview.candidate_email,
    scheduledAt: interview.scheduled_at,
    durationMinutes: interview.duration_minutes,
    status: interview.status,
    provider: interview.provider,
    meetingUrl: interview.meeting_url,
    cachedAt: new Date().toISOString(),
  };
  writeCache(cache);
}

export function updateCachedInterviewResponse(
  applicationId: string,
  invitationStatus: string,
  candidateResponse: string,
) {
  const cache = readCache();
  const existing = cache[applicationId];
  if (!existing) return;
  existing.invitationStatus = invitationStatus;
  existing.candidateResponse = candidateResponse;
  writeCache(cache);
}

/** Manual booking path — caches the result immediately since it's otherwise unrecoverable. */
export async function bookInterview(payload: InterviewCreate): Promise<InterviewRead> {
  const interview = await createInterviewApi(payload);
  cacheInterviewFromInline(interview);
  return interview;
}
