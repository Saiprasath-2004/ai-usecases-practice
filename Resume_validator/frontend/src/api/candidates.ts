import api from './client';
import type { EvaluationStatusRead } from '../types';

// The original single-resume flow. It runs independently of the job /
// application model (no job_requisition_id, no Application row) — kept
// here as a "Quick Evaluate" utility since it's still fully functional.

export async function startEvaluation(jdPath: string, resumePath: string): Promise<{ id: string; status: string }> {
  const { data } = await api.post('/candidates', {
    jd_path: jdPath,
    resume_path: resumePath,
  });
  return data;
}

export async function fetchEvaluationStatus(id: string): Promise<EvaluationStatusRead> {
  const { data } = await api.get(`/candidates/${id}`);
  return data;
}

export async function submitFollowupReply(id: string, replyText: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/candidates/${id}/followup-reply`, {
    reply_text: replyText,
  });
  return data;
}

export async function submitReview(
  id: string,
  decision: 'Approve' | 'Reject' | 'Request More Info',
  comments: string
): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/candidates/${id}/review`, {
    decision,
    comments,
  });
  return data;
}
