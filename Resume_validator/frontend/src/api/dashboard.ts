import type { FlatApplication } from '../hooks/useAllApplications';
import type { JobRead } from '../types';
import { listCachedInterviews } from './interviews';

/**
 * There is no GET /dashboard aggregation endpoint. Every number here is
 * computed client-side from GET /jobs + GET /jobs/{id}/applications (see
 * useAllApplications) — nothing is fabricated, but "Upcoming Interviews"
 * is only as complete as the local interview cache in api/interviews.ts,
 * since the backend has no interview-list endpoint either.
 */
export interface DashboardSummary {
  totalJobs: number;
  totalCandidates: number;
  evaluated: number;
  strongMatches: number;
  needsReview: number;
  onHold: number;
  rejected: number;
  upcomingInterviews: number;
  pendingHumanReview: number;
}

export function summarizeDashboard(jobs: JobRead[], flat: FlatApplication[]): DashboardSummary {
  const now = Date.now();
  const upcomingInterviews = listCachedInterviews().filter(
    (i) => new Date(i.scheduledAt).getTime() > now && i.status !== 'Cancelled',
  ).length;

  return {
    totalJobs: jobs.length,
    totalCandidates: flat.length,
    evaluated: flat.filter((a) => a.evaluation_status === 'Completed').length,
    strongMatches: flat.filter((a) => a.pipeline_stage === 'Shortlisted').length,
    needsReview: flat.filter((a) => a.pipeline_stage === 'Needs Review').length,
    onHold: flat.filter((a) => a.pipeline_stage === 'On Hold').length,
    rejected: flat.filter((a) => a.pipeline_stage === 'Rejected').length,
    upcomingInterviews,
    // "Pending human review" = has actually been evaluated and is sitting
    // in Needs Review, as distinct from a fresh application nobody has
    // evaluated yet (evaluation_status Pending).
    pendingHumanReview: flat.filter(
      (a) => a.pipeline_stage === 'Needs Review' && a.evaluation_status === 'Completed',
    ).length,
  };
}

export interface RecentJobRow {
  job: JobRead;
  candidateCount: number;
  evaluatedCount: number;
}

export function buildRecentJobs(jobs: JobRead[], flat: FlatApplication[], limit = 5): RecentJobRow[] {
  return jobs
    .slice()
    .sort((a, b) => b.id - a.id)
    .slice(0, limit)
    .map((job) => {
      const forJob = flat.filter((a) => a.jobId === job.id);
      return {
        job,
        candidateCount: forJob.length,
        evaluatedCount: forJob.filter((a) => a.evaluation_status === 'Completed').length,
      };
    });
}
