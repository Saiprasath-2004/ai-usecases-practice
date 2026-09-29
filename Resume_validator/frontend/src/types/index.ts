// Mirrors ats_agent.domain.models + ats_agent.api.schemas exactly as they
// exist in the backend source. Do not add fields the backend doesn't
// actually return — see README "Backend limitations" for the gaps.

// ============================================================
// Enums (ats_agent.domain.models)
// ============================================================

export type PipelineStage = 'Shortlisted' | 'Needs Review' | 'Rejected' | 'On Hold';

export const PIPELINE_STAGES: PipelineStage[] = [
  'Shortlisted',
  'Needs Review',
  'On Hold',
  'Rejected',
];

export type EvaluationStatus = 'Pending' | 'Running' | 'Completed' | 'Failed';

export type RunStatus =
  | 'Pending'
  | 'Running'
  | 'Waiting for Review'
  | 'Completed'
  | 'Failed';

// The six decisions the LangGraph human-review interrupt declares as
// ALLOWED_DECISIONS. Not all six currently have a working API path —
// see api/applications.ts and the README for which ones actually work.
export type ReviewDecision =
  | 'Schedule Interview'
  | 'Get More Details'
  | 'Hold'
  | 'Reject'
  | 'Move to Review'
  | 'Confirm Rejection';

// ============================================================
// Jobs
// ============================================================

export interface JobRead {
  id: number;
  title: string;
  department: string;
  location: string;
  employment_type: string;
  job_description_text: string;
  job_description_source: string;
  required_skills: string;
  evaluation_status: string;
}

export interface JobCreate {
  title: string;
  department: string;
  location: string;
  employment_type: string;
  job_description_text: string;
  job_description_source: string;
  required_skills?: string;
}

// ============================================================
// Applications
// ============================================================

// What GET /applications/{id} and GET /jobs/{id}/applications actually
// return today (api/schemas/applications.py::ApplicationRead).
export interface ApplicationRead {
  application_id: string;
  candidate_name: string;
  candidate_email: string;
  resume_path: string;
  pipeline_stage: PipelineStage;
  evaluation_status: EvaluationStatus;
  overall_score: number | null;

  // JSON-encoded strings on the backend — parse with asList()/asRecord()
  // from lib/format.ts before rendering. Never assume these are already
  // arrays/objects.
  score_breakdown?: string | null;
  matched_skills?: string | null;
  missing_skills?: string | null;
  strengths?: string | null;
  gaps?: string | null;
  responsibilities_matched?: string | null;
  responsibilities_missing?: string | null;
  experience_result?: string | null;

  recruiter_comments?: string | null;
  follow_up_status?: string | null;
  interview_status?: string | null;
  thread_id?: string | null;
  current_evaluation_run_id?: number | null;
}

// GET /applications/job/{job_id} has no response_model, so it serializes
// the raw Application table row — a superset of ApplicationRead with a
// few extra internal columns. Used only where that extra data helps
// (e.g. submission_date for a timeline).
export interface ApplicationRaw extends ApplicationRead {
  job_requisition_id?: number | null;
  candidate_id?: number | null;
  submission_date?: string;
}

export type ApplicationBoard = Partial<Record<PipelineStage, ApplicationRead[]>>;

export interface ApplicationCreate {
  job_requisition_id: number;
  candidate_name: string;
  candidate_email: string;
  resume_path: string;
}

export interface EvaluationResponse {
  status: string;
  application_id: string;
  evaluation_status: EvaluationStatus;
  pipeline_stage: PipelineStage;
  overall_score: number | null;
  thread_id: string | null;
  run_id: number | null;
  run_status: RunStatus | null;
}

// Score breakdown, once JSON.parse()'d — mirrors ats_agent scorer output.
export interface ScoreBreakdown {
  overall_score?: number | null;
  skill_score?: number | null;
  experience_score?: number | null;
  keyword_score?: number | null;
  responsibility_score?: number | null;
}

// experience_result, once JSON.parse()'d.
export interface ExperienceResult {
  candidate_years?: number | null;
  required_min_years?: number | null;
  required_max_years?: number | null;
  status?: string | null;
  matches_requirement?: boolean | null;
}

// ============================================================
// Recruiter actions
// ============================================================

// The generic, side-effect-free pipeline mover (POST /applications/{id}/actions).
// Only these action_type strings are recognized by
// map_action_to_domain_type / map_recruiter_action_to_stage on the backend.
export type PipelineActionType =
  | 'HOLD'
  | 'REJECT'
  | 'MOVE_TO_REVIEW'
  | 'SHORTLIST'
  | 'SCHEDULE_INTERVIEW'
  | 'GET_MORE_DETAILS';

export interface ActionRequest {
  action_type: PipelineActionType;
  note?: string;
}

export interface ActionResponse {
  status: string;
  application_id: string;
  action: string;
  pipeline_stage: PipelineStage;
}

// POST /applications/{id}/hold — a plain state flip, no thread required.
export interface HoldResponse {
  status: string;
  application_id: string;
  pipeline_stage: PipelineStage;
}

// POST /applications/{id}/reject — requires an existing thread_id (the
// backend 400s otherwise) and sends a real rejection email.
export interface RejectResponse {
  status: string;
  application_id: string;
  pipeline_stage: PipelineStage;
  communication: { action_id: string | null; status: string | null };
}

// The LangGraph-backed decision endpoint (POST /applications/{id}/review).
// decision must be one of ALLOWED_DECISIONS, but only 'Schedule Interview',
// 'Get More Details', 'Hold' and 'Reject' currently map to a valid backend
// ActionType — see README.
export interface ReviewRequest {
  decision: ReviewDecision;
  comments?: string;
  scheduled_at?: string;
  duration_minutes?: number;
}

export interface ReviewResponse {
  status: string;
  application_id: string;
  action: string;
  pipeline_stage: PipelineStage;
  thread_id: string | null;
  interview: InterviewInline | null;
  communication: {
    action_id: string | null;
    status: string | null;
  };
}

export interface FollowupReplyRequest {
  candidate_reply: string;
}

// The evidence bundle built by ats_agent.agent_layer.report — richer than
// ApplicationRead's flat matched/missing lists, but ONLY reachable via the
// workflow_state on a followup-reply response (see FollowupReplyResponse).
export interface Evidence {
  skills: { matched: string[]; missing: string[]; coverage: number };
  keywords: { matched: string[]; missing: string[] };
  responsibilities: { matched: string[]; missing: string[] };
  experience: {
    candidate_years: number | null;
    required_min_years: number | null;
    required_max_years: number | null;
    status: string | null;
  };
  score_breakdown: ScoreBreakdown;
}

// The raw LangGraph state (ats_agent.graph.state.ATSState), returned in
// full and unfiltered only by POST /followup-reply as "workflow_state".
// This is the one place `verdict` and `narrative` are ever exposed by the
// API today — see README "AI verdict & narrative" for why every other
// screen has to go without them.
export interface WorkflowState {
  verdict?: 'SELECT' | 'ESCALATE' | 'REJECT' | null;
  escalation_reason?: string | null;
  evidence?: Evidence | null;
  narrative?: string | null;
  followup_questions?: string[] | null;
  human_decision?: string | null;
  human_comments?: string | null;
}

export interface FollowupReplyResponse {
  status: string;
  application_id: string;
  thread_id: string | null;
  overall_score: number | null;
  verdict: string | null;
  pipeline_stage: PipelineStage;
  workflow_state: WorkflowState;
}

export interface InterviewResponseRequest {
  response: 'ACCEPTED' | 'DECLINED';
}

// ============================================================
// Interviews
// ============================================================

// The shape embedded inline in a POST /review response when the decision
// was "Schedule Interview". This is the ONLY place the frontend ever sees
// this data — there is no GET endpoint to read it back later. Notably
// missing invitation_status/candidate_response even though the backend
// sets them (see README "Interviews" limitation).
export interface InterviewInline {
  id: number;
  application_id: string;
  recruiter_id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  provider: string | null;
  external_event_id: string | null;
  meeting_url: string | null;
  candidate_email: string;
  notes: string | null;
}

// The shape returned by the manual booking path, POST /calendar/interviews.
export interface InterviewRead {
  id: number;
  application_id: string;
  recruiter_id: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  provider: string | null;
  external_event_id: string | null;
  meeting_url: string | null;
  candidate_email: string;
  notes: string | null;
}

export interface InterviewCreate {
  application_id: string;
  recruiter_id: string;
  scheduled_at: string;
  duration_minutes?: number;
  candidate_email: string;
  provider?: string;
  meeting_url?: string;
  notes?: string;
}

// The full interview response shape from POST /applications/{id}/interview/respond.
export interface InterviewRespondResult {
  status: string;
  application_id: string;
  interview: {
    id: number;
    scheduled_at: string;
    duration_minutes: number;
    status: string;
    invitation_status: string;
    candidate_response: string;
    candidate_responded_at: string | null;
    meeting_url: string | null;
  };
}

// ============================================================
// Calendar
// ============================================================

export interface AvailabilityRead {
  id: number | null;
  recruiter_id: string;
  day_of_week: number; // Monday = 0 ... Sunday = 6
  start_time: string; // HH:MM:SS
  end_time: string;
  active: boolean;
}

export interface AvailabilityCreate {
  recruiter_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  active?: boolean;
}

export interface AvailabilityUpdate {
  start_time?: string;
  end_time?: string;
  active?: boolean;
}

export interface CalendarBlockRead {
  id: number | null;
  recruiter_id: string;
  start_at: string;
  end_at: string;
  all_day: boolean;
  reason: string | null;
}

export interface CalendarBlockCreate {
  recruiter_id: string;
  start_at: string;
  end_at: string;
  all_day?: boolean;
  reason?: string;
}

export interface FullDayBlockCreate {
  recruiter_id: string;
  target_date: string;
  reason?: string;
}

export interface AvailableSlot {
  start: string;
  end: string;
}

export interface AvailableSlotsResponse {
  recruiter_id: string;
  target_date: string;
  duration_minutes: number;
  slots: AvailableSlot[];
}

export const WEEKDAY_LABELS = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

// The single hardcoded recruiter this prototype operates as
// (matches recruiter_id="recruiter_1" in api/routes/applications.py's
// scheduling call). No auth/multi-recruiter support exists yet.
export const RECRUITER_ID = 'recruiter_1';

// ============================================================
// Frontend-derived types (NOT backend response shapes)
// ============================================================

// Notifications have no backend model — these are synthesized client-side
// from application/job data. Kept separate from backend types so it's
// obvious at a glance this isn't an API contract.
export type DerivedNotificationKind =
  | 'evaluation_failed'
  | 'needs_review'
  | 'on_hold'
  | 'follow_up_sent'
  | 'interview_scheduled';

export interface DerivedNotification {
  id: string;
  kind: DerivedNotificationKind;
  title: string;
  detail: string;
  jobId: number;
  applicationId: string;
  candidateName: string;
}
