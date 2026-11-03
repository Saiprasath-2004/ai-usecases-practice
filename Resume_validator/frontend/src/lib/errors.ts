import { AxiosError } from 'axios';

// Known server messages mapped to plain recruiter language. Anything that
// isn't a short, readable sentence falls back to a generic message so raw
// technical text (tracebacks, workflow internals) never reaches the screen.
const FRIENDLY_MESSAGES: [RegExp, string][] = [
  [/thread/i, 'Run an evaluation for this candidate first.'],
  [/already running/i, 'An evaluation is already in progress for this candidate.'],
  [/comments are required when scheduling/i, 'Add a scheduling instruction first, for example "next Tuesday afternoon".'],
  [/invalid action type/i, "That action isn't available right now."],
  [/failed to schedule interview/i, "We couldn't schedule the interview. Try a different day or time."],
  [/invitation could not be sent|invitation has not been|notification failed|candidate has not been notified/i, "The interview wasn't confirmed because the invitation couldn't be sent to the candidate. Please try again."],
  [/already responded/i, 'The candidate has already responded to this interview.'],
  [/no scheduled interview/i, 'There is no scheduled interview for this candidate.'],
  [/not associated with a job|job.*not found|job description source/i, "This job isn't set up correctly yet."],
];

const TECHNICAL = /traceback|exception|error:|langgraph|workflow|sqlalchemy|\bapi\b|endpoint|database|backend/i;

function friendlyDetail(detail: string | undefined): string | null {
  if (!detail) return null;
  for (const [pattern, message] of FRIENDLY_MESSAGES) {
    if (pattern.test(detail)) return message;
  }
  if (detail.length <= 140 && !TECHNICAL.test(detail)) return detail;
  return null;
}

/**
 * Turn any thrown error into a short, recruiter-facing message.
 * `detail` keeps the raw text for debugging but is never shown in normal UI.
 */
export function describeError(error: unknown): { message: string; detail?: string } {
  if (error instanceof AxiosError) {
    const status = error.response?.status;
    const data = error.response?.data as { detail?: unknown } | undefined;
    const rawDetail =
      typeof data?.detail === 'string'
        ? data.detail
        : data?.detail
          ? JSON.stringify(data.detail)
          : error.message;

    if (!error.response) {
      return {
        message: "We couldn't complete that request. Check your connection and try again.",
        detail: error.message,
      };
    }
    const friendly = friendlyDetail(typeof data?.detail === 'string' ? data.detail : undefined);
    if (friendly) return { message: friendly, detail: rawDetail };
    if (status === 404) return { message: "We couldn't find that record.", detail: rawDetail };
    if (status === 409) {
      return { message: "That couldn't be completed. Adjust your request and try again.", detail: rawDetail };
    }
    if (status && status >= 500) {
      return { message: 'Something went wrong on our side. Please try again.', detail: rawDetail };
    }
    return { message: 'Something went wrong. Please try again.', detail: rawDetail };
  }
  if (error instanceof Error) {
    return { message: 'Something went wrong. Please try again.', detail: error.message };
  }
  return { message: 'Something went wrong. Please try again.' };
}
