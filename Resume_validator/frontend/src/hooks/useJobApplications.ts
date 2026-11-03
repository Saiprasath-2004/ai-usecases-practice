import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listJobApplications } from '../api/jobs';
import { flattenBoard } from '../lib/board';
import type { ApplicationRead } from '../types';

export interface JobApplicationsResult {
  applications: ApplicationRead[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
  /** True while at least one candidate is being evaluated. */
  evaluating: boolean;
  dataUpdatedAt: number;
}

/**
 * The single source of candidate data for one job. The Jobs list, the job
 * page and the dashboard all read this same query (same key, same
 * flattening), so their counts always agree. While an evaluation is
 * running it refreshes every few seconds until the states settle.
 */
export function useJobApplications(jobId: number, options: { poll?: boolean } = {}): JobApplicationsResult {
  const query = useQuery({
    queryKey: ['job-applications', jobId],
    queryFn: () => listJobApplications(jobId),
    enabled: Number.isFinite(jobId),
    refetchInterval: (q) =>
      options.poll || flattenBoard(q.state.data).some((a) => a.evaluation_status === 'Running') ? 2500 : false,
  });

  const applications = useMemo(() => flattenBoard(query.data), [query.data]);

  return {
    applications,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: () => {
      void query.refetch();
    },
    evaluating: applications.some((a) => a.evaluation_status === 'Running'),
    dataUpdatedAt: query.dataUpdatedAt,
  };
}
