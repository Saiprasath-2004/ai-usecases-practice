import type { FlatApplication } from '../hooks/useAllApplications';
import type { DerivedNotification } from '../types';
import { hasStatus, humanize } from '../lib/format';
import { listCachedInterviews } from './interviews';

/**
 * There is no notification model or endpoint on the backend at all.
 * Everything here is synthesized, on every render, from the current state
 * of applications (and the local interview cache) — nothing is stored, so
 * there's no "mark as read" or history; a notification simply disappears
 * once the underlying condition it describes is no longer true. Each one
 * links back to the application/job it came from.
 *
 * If a real notifications endpoint is added later, this file is the only
 * place that needs to change — pages consume deriveNotifications()'s
 * output shape (DerivedNotification[]), not the raw application data.
 */
export function deriveNotifications(flat: FlatApplication[]): DerivedNotification[] {
  const notifications: DerivedNotification[] = [];

  for (const app of flat) {
    if (app.evaluation_status === 'Failed') {
      notifications.push({
        id: `eval-failed-${app.application_id}`,
        kind: 'evaluation_failed',
        title: 'Evaluation failed',
        detail: `${app.candidate_name}'s evaluation for ${app.jobTitle} did not complete. Re-run it from the candidate table.`,
        jobId: app.jobId,
        applicationId: app.application_id,
        candidateName: app.candidate_name,
      });
    }

    if (app.pipeline_stage === 'Needs Review' && app.evaluation_status === 'Completed') {
      notifications.push({
        id: `needs-review-${app.application_id}`,
        kind: 'needs_review',
        title: 'Waiting for your review',
        detail: `${app.candidate_name} (${app.jobTitle}) has a completed evaluation and needs a recruiter decision.`,
        jobId: app.jobId,
        applicationId: app.application_id,
        candidateName: app.candidate_name,
      });
    }

    if (app.pipeline_stage === 'On Hold') {
      notifications.push({
        id: `on-hold-${app.application_id}`,
        kind: 'on_hold',
        title: 'On hold',
        detail: `${app.candidate_name} (${app.jobTitle}) is on hold and may need a follow-up decision.`,
        jobId: app.jobId,
        applicationId: app.application_id,
        candidateName: app.candidate_name,
      });
    }

    if (hasStatus(app.follow_up_status)) {
      notifications.push({
        id: `follow-up-${app.application_id}-${app.follow_up_status}`,
        kind: 'follow_up_sent',
        title: 'Follow-up in progress',
        detail: `${app.candidate_name} (${app.jobTitle}) follow-up: ${humanize(app.follow_up_status)}.`,
        jobId: app.jobId,
        applicationId: app.application_id,
        candidateName: app.candidate_name,
      });
    }
  }

  // Interview events can only be derived for interviews this browser has
  // itself booked or recorded a response for — see api/interviews.ts.
  for (const interview of listCachedInterviews()) {
    if (interview.candidateResponse === 'ACCEPTED' || interview.candidateResponse === 'DECLINED') {
      notifications.push({
        id: `interview-response-${interview.applicationId}`,
        kind: 'interview_scheduled',
        title: interview.candidateResponse === 'ACCEPTED' ? 'Interview accepted' : 'Interview declined',
        detail: `Candidate ${interview.candidateResponse === 'ACCEPTED' ? 'accepted' : 'declined'} the interview scheduled for ${new Date(interview.scheduledAt).toLocaleString()}.`,
        jobId: 0,
        applicationId: interview.applicationId,
        candidateName: interview.candidateEmail,
      });
    }
  }

  return notifications;
}
