import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, MapPin, Building2, PlayCircle, Users } from 'lucide-react';
import { getJob, listJobApplications, triggerBulkEvaluation } from '../api/jobs';
import { EmptyState, PageError, ScoreRing, Spinner, StageBadge } from '../components/Primitives';
import { PIPELINE_STAGES, type ApplicationRead } from '../types';
import { useToast } from '../components/Toast';

export default function JobDetailPage() {
  const { jobId, appId } = useParams();
  const id = Number(jobId);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { push } = useToast();
  const [running, setRunning] = useState(false);

  const jobQuery = useQuery({ queryKey: ['job', id], queryFn: () => getJob(id), enabled: !Number.isNaN(id) });
  const appsQuery = useQuery({
    queryKey: ['job-applications', id],
    queryFn: () => listJobApplications(id),
    enabled: !Number.isNaN(id),
    refetchInterval: running ? 4000 : false,
  });

  const bulkEval = useMutation({
    mutationFn: () => triggerBulkEvaluation(id),
    onSuccess: (res) => {
      push('success', res.message || 'Bulk evaluation started.');
      setRunning(true);
      qc.invalidateQueries({ queryKey: ['job-applications', id] });
      window.setTimeout(() => setRunning(false), 60000);
    },
    onError: (err: unknown) => {
      push('error', extractError(err, 'Could not start bulk evaluation.'));
    },
  });

  const board = appsQuery.data;
  const totalApps = board ? Object.values(board).reduce((sum, list) => sum + (list?.length ?? 0), 0) : 0;

  return (
    <div>
      <Link to="/" className="focus-ring inline-flex items-center gap-1.5 text-sm text-ink-faint hover:text-ink">
        <ArrowLeft className="h-3.5 w-3.5" /> All jobs
      </Link>

      {jobQuery.isLoading && (
        <div className="mt-8 flex items-center gap-2 text-ink-faint">
          <Spinner className="h-5 w-5" /> Loading job…
        </div>
      )}

      {jobQuery.isError && (
        <div className="mt-6">
          <PageError message={(jobQuery.error as Error)?.message || 'Could not load job.'} onRetry={() => jobQuery.refetch()} />
        </div>
      )}

      {jobQuery.data && (
        <header className="mt-4 flex flex-col justify-between gap-4 border-b border-line pb-6 md:flex-row md:items-end">
          <div className="min-w-0">
            <h1 className="font-display text-3xl text-ink">{jobQuery.data.title}</h1>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-ink-faint">
              <span className="flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5" /> {jobQuery.data.department}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" /> {jobQuery.data.location}
              </span>
              <span className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" /> {totalApps} applicant{totalApps === 1 ? '' : 's'}
              </span>
            </div>
          </div>

          <button
            onClick={() => bulkEval.mutate()}
            disabled={bulkEval.isPending}
            className="focus-ring inline-flex items-center gap-2 self-start rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {bulkEval.isPending ? <Spinner className="h-4 w-4" /> : <PlayCircle className="h-4 w-4" />}
            Run bulk evaluation
          </button>
        </header>
      )}

      {appsQuery.isLoading && (
        <div className="mt-10 flex items-center gap-2 text-ink-faint">
          <Spinner className="h-5 w-5" /> Loading applicants…
        </div>
      )}

      {appsQuery.isError && (
        <div className="mt-6">
          <PageError message={(appsQuery.error as Error)?.message || 'Could not load applications.'} onRetry={() => appsQuery.refetch()} />
        </div>
      )}

      {board && totalApps === 0 && (
        <div className="mt-8">
          <EmptyState
            title="No applications for this job yet"
            description="Applications are created directly against the database today — there isn't an “apply” endpoint on the backend yet."
          />
        </div>
      )}

      {board && totalApps > 0 && (
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {PIPELINE_STAGES.map((stage) => (
            <PipelineColumn
              key={stage}
              stage={stage}
              applications={board[stage] ?? []}
              jobId={id}
              activeAppId={appId}
              onOpen={(app) => navigate(`/jobs/${id}/applications/${app.application_id}`)}
            />
          ))}
        </div>
      )}

      <Outlet context={{ jobId: id }} />
    </div>
  );
}

function PipelineColumn({
  stage,
  applications,
  activeAppId,
  onOpen,
}: {
  stage: ApplicationRead['pipeline_stage'];
  applications: ApplicationRead[];
  jobId: number;
  activeAppId?: string;
  onOpen: (app: ApplicationRead) => void;
}) {
  return (
    <div className="flex flex-col rounded-card border border-line bg-panel/50">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <StageBadge stage={stage} />
        <span className="font-mono text-xs text-ink-faint">{applications.length}</span>
      </div>
      <div className="scrollbar-thin flex max-h-[70vh] flex-col gap-2.5 overflow-y-auto p-3">
        {applications.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-ink-faint">No candidates here.</p>
        )}
        {applications.map((app) => (
          <button
            key={app.application_id}
            onClick={() => onOpen(app)}
            className={`focus-ring flex items-center gap-3 rounded-md border bg-white px-3 py-2.5 text-left shadow-card transition-colors hover:border-ink/20 ${
              activeAppId === app.application_id ? 'border-ink' : 'border-line'
            }`}
          >
            <ScoreRing score={app.overall_score} size={38} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink">{app.candidate_name}</p>
              <p className="truncate text-xs text-ink-faint">{app.candidate_email}</p>
            </div>
            <StatusDot status={app.evaluation_status} />
          </button>
        ))}
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: ApplicationRead['evaluation_status'] }) {
  const color =
    status === 'Completed'
      ? 'bg-moss-500'
      : status === 'Failed'
      ? 'bg-rust-500'
      : status === 'Running'
      ? 'bg-amber-500 animate-pulse'
      : 'bg-ink-faint/50';
  return <span title={status} className={`ml-auto h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

export function extractError(err: unknown, fallback: string): string {
  const anyErr = err as { response?: { data?: { detail?: string } }; message?: string };
  return anyErr?.response?.data?.detail || anyErr?.message || fallback;
}
