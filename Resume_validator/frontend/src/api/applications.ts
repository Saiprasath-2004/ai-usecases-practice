import api from './client';
import type {
  ActionRequest,
  ActionResponse,
  ApplicationCreate,
  ApplicationRaw,
  ApplicationRead,
  EvaluationResponse,
  FollowupReplyRequest,
  FollowupReplyResponse,
  HoldResponse,
  InterviewResponseRequest,
  InterviewRespondResult,
  RejectResponse,
  ReviewRequest,
  ReviewResponse,
} from '../types';

export async function createApplication(payload: ApplicationCreate): Promise<ApplicationRead> {
  const { data } = await api.post('/applications', payload);
  return data;
}

/** Flat, unsorted, includes a few raw columns ApplicationRead omits (e.g. submission_date). */
export async function listApplicationsForJob(jobId: number): Promise<ApplicationRaw[]> {
  const { data } = await api.get(`/applications/job/${jobId}`);
  return data;
}

export async function getApplication(applicationId: string): Promise<ApplicationRead> {
  const { data } = await api.get(`/applications/${applicationId}`);
  return data;
}

/**
 * Runs the LangGraph workflow synchronously and blocks until it pauses at
 * human review (or fails). Returns 409 if this application is already
 * mid-evaluation.
 */
export async function evaluateApplication(applicationId: string): Promise<EvaluationResponse> {
  const { data } = await api.post(`/applications/${applicationId}/evaluate`);
  return data;
}

/**
 * Resumes the human-review interrupt. Only 'Schedule Interview',
 * 'Get More Details', 'Hold' and 'Reject' currently map to a valid backend
 * ActionType — 'Move to Review' and 'Confirm Rejection' will 400 here (see
 * moveToReview() below and the README). Requires the application to already
 * have a thread_id (i.e. it has been evaluated at least once).
 */
export async function submitReview(
  applicationId: string,
  payload: ReviewRequest,
): Promise<ReviewResponse> {
  const { data } = await api.post(`/applications/${applicationId}/review`, payload);
  return data;
}

/**
 * Resumes the candidate follow-up interrupt with their reply, triggers a
 * rescore, and — uniquely among these endpoints — returns the full
 * workflow_state, which is the only place `verdict`/`narrative` are ever
 * exposed by this API.
 */
export async function submitFollowupReply(
  applicationId: string,
  payload: FollowupReplyRequest,
): Promise<FollowupReplyResponse> {
  const { data } = await api.post(`/applications/${applicationId}/followup-reply`, payload);
  return data;
}

export async function respondToInterview(
  applicationId: string,
  payload: InterviewResponseRequest,
): Promise<InterviewRespondResult> {
  const { data } = await api.post(`/applications/${applicationId}/interview/respond`, payload);
  return data;
}

/** Convenience shortcut — no thread_id required. */
export async function holdApplication(applicationId: string): Promise<HoldResponse> {
  const { data } = await api.post(`/applications/${applicationId}/hold`);
  return data;
}

/** Convenience shortcut — requires an existing thread_id, sends a real rejection email. */
export async function rejectApplication(applicationId: string): Promise<RejectResponse> {
  const { data } = await api.post(`/applications/${applicationId}/reject`);
  return data;
}

/** The generic, side-effect-free pipeline mover. This is the only working path for "Move to Review". */
export async function performAction(
  applicationId: string,
  payload: ActionRequest,
): Promise<ActionResponse> {
  const { data } = await api.post(`/applications/${applicationId}/actions`, payload);
  return data;
}

/** "Move to Review" 400s through /review (see submitReview) — /actions is the only endpoint that accepts it. */
export async function moveToReview(applicationId: string, note?: string): Promise<ActionResponse> {
  return performAction(applicationId, { action_type: 'MOVE_TO_REVIEW', note });
}
