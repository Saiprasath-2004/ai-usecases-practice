/**
 * Follow-up activity record.
 *
 * The application record does not carry a usable follow-up status, so this
 * remembers which candidates this recruiter has asked for more details (and
 * whether a reply has been recorded). It only feeds the "Follow-up" filter
 * and the follow-up card; the candidate's real evaluation data always comes
 * from the application itself.
 */
const STORAGE_KEY = 'ats_frontend_followup_activity_v1';

export interface FollowupActivity {
  applicationId: string;
  requestedAt: string;
  deliveryStatus: string | null;
  repliedAt?: string;
}

function read(): Record<string, FollowupActivity> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function write(data: Record<string, FollowupActivity>) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Storage unavailable — activity simply won't persist across reloads.
  }
}

export function recordFollowupRequested(applicationId: string, deliveryStatus: string | null) {
  const data = read();
  data[applicationId] = { applicationId, requestedAt: new Date().toISOString(), deliveryStatus };
  write(data);
}

export function recordFollowupReplied(applicationId: string) {
  const data = read();
  const existing = data[applicationId] ?? {
    applicationId,
    requestedAt: new Date().toISOString(),
    deliveryStatus: null,
  };
  data[applicationId] = { ...existing, repliedAt: new Date().toISOString() };
  write(data);
}

export function getFollowupActivity(applicationId: string): FollowupActivity | null {
  return read()[applicationId] ?? null;
}

export function listFollowupActivity(): FollowupActivity[] {
  return Object.values(read());
}
