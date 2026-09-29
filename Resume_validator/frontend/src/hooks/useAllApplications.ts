import { useQueries, useQuery } from '@tanstack/react-query';
import { listJobApplications, listJobs } from '../api/jobs';
import { flattenBoard } from '../lib/board';
import type { ApplicationBoard, ApplicationRead, JobRead } from '../types';

export interface FlatApplication extends ApplicationRead {
  jobId: number;
  jobTitle: string;
}

export interface AllApplicationsResult {
  jobs: JobRead[];
  boardsByJob: Record<number, ApplicationBoard>;
  flat: FlatApplication[];
  isLoading: boolean;
  /** The job list itself failed to load — nothing can be shown. */
  isError: boolean;
  /** Some jobs' candidates failed to load, so totals may be incomplete. */
  partial: boolean;
}


/**
 * Candidates across every job (Dashboard, Candidates, Recruiter Review,
 * Notifications, Analytics). It reads the same per-job queries as
 * useJobApplications, so totals here always match each job's own page.
 */
export function useAllApplications(): AllApplicationsResult {
  const jobsQuery = useQuery({ queryKey: ['jobs'], queryFn: listJobs });
  const jobs = jobsQuery.data ?? [];

  const boardQueries = useQueries({
    queries: jobs.map((job) => ({
      queryKey: ['job-applications', job.id],
      queryFn: () => listJobApplications(job.id),
      enabled: jobsQuery.isSuccess,
    })),
  });

  const boardsByJob: Record<number, ApplicationBoard> = {};
  const flat: FlatApplication[] = [];

  jobs.forEach((job, index) => {
    const board = boardQueries[index]?.data;
    if (board) {
      boardsByJob[job.id] = board;
      flat.push(...flattenBoard(board).map((a) => ({ ...a, jobId: job.id, jobTitle: job.title })));
    }
  });

  return {
    jobs,
    boardsByJob,
    flat,
    isLoading: jobsQuery.isLoading || boardQueries.some((q) => q.isLoading),
    isError: jobsQuery.isError,
    partial: boardQueries.some((q) => q.isError),
  };
}
