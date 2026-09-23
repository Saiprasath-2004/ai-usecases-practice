// Mirrors ats_agent.domain.models + ats_agent.api.schemas

export type PipelineStage = 'Shortlisted' | 'Needs Review' | 'Rejected' | 'On Hold';

export const PIPELINE_STAGES: PipelineStage[] = [
  'Shortlisted',
  'Needs Review',
  'On Hold',
  'Rejected',
];

export type EvaluationStatus = 'Pending' | 'Running' | 'Completed' | 'Failed';

export interface JobRead {
  id: number;
  title: string;
  department: string;
  location: string;
  employment_type: string;
  job_description_text: string;
  job_description_source: string;
  evaluation_status: string;
}

// What GET /applications/{id} and the job board actually return today.
export interface ApplicationRead {
  application_id: string;
  candidate_name: string;
  candidate_email: string;
  pipeline_stage: PipelineStage;
  overall_score: number | null;
  evaluation_status: EvaluationStatus;
  evaluation_verdict: string | null;
  resume_path: string;

  // Not yet exposed by ApplicationRead on the backend (the Application table
  // stores them, but the response_model currently strips them out). The UI
  // below reads these defensively and falls back gracefully when absent —
  // see the README note on extending ApplicationRead.
  score_breakdown?: string | Record<string, number> | null;
  matched_skills?: string | string[] | null;
  missing_skills?: string | string[] | null;
  strengths?: string | string[] | null;
  gaps?: string | string[] | null;
  responsibilities_matched?: string | string[] | null;
  responsibilities_missing?: string | string[] | null;
  experience_result?: string | Record<string, unknown> | null;
  recruiter_comments?: string | null;
  follow_up_status?: string | null;
  interview_status?: string | null;
}

export type ApplicationBoard = Partial<Record<PipelineStage, ApplicationRead[]>>;

export type RecruiterActionType = 'SHORTLIST' | 'HOLD' | 'REJECT' | 'MOVE_TO_REVIEW';

// --- Legacy single-candidate evaluation flow (POST /candidates) ---

export type QuickEvalStatus =
  | 'running'
  | 'awaiting_followup'
  | 'awaiting_review'
  | 'completed'
  | 'failed';

export interface EvaluationStatusRead {
  id: string;
  status: QuickEvalStatus;
  current_node: string | null;
  verdict: string | null;
  followup_questions: string[] | null;
  narrative: string | null;
  error: string | null;
}
