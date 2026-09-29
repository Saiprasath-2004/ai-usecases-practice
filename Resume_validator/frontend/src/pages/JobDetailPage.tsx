import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { FileText, PlayCircle } from 'lucide-react';
import { getJob, triggerBulkEvaluation } from '../api/jobs';
import { evaluateApplication } from '../api/applications';
import { useJobApplications } from '../hooks/useJobApplications';
import { asList } from '../lib/format';
import { describeError } from '../lib/errors';
import { useToast } from '../components/Toast';
import {
  Badge,
  Breadcrumbs,
  Button,
  EmptyState,
  LoadingState,
  Notice,
  PageError,
  PageHeader,
  SectionCard,
  Tabs,
} from '../components/Primitives';
import { CandidateTable } from '../components/candidates/CandidateTable';
import { EvaluationResultsTable } from '../components/candidates/EvaluationResultsTable';

const TABS = [
  { id: 'candidates', label: 'Candidates' },
  { id: 'evaluation-results', label: 'Evaluation Results' },
  { id: 'recruiter-review', label: 'Recruiter Review' },
  { id: 'job-details', label: 'Job Details' },
];

const BULK_POLL_LIMIT_MS = 10 * 60 * 1000;

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const id = Number(jobId);
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('candidates');
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [showDescription, setShowDescription] = useState(false);
  const [bulkStartedAt, setBulkStartedAt] = useState<number | null>(null);

  const jobQuery = useQuery({ queryKey: ['job', id], queryFn: () => getJob(id), enabled: Number.isFinite(id) });
  const { applications: all, isLoading, isError, error, refetch, dataUpdatedAt } = useJobApplications(id, {
    poll: bulkStartedAt !== null,
  });

  const notEvaluated = all.filter((a) => a.evaluation_status === 'Pending').length;
  const evaluating = all.filter((a) => a.evaluation_status === 'Running').length;
  const completed = all.filter((a) => a.evaluation_status === 'Completed').length;
  const failed = all.filter((a) => a.evaluation_status === 'Failed').length;
  const waitingForReview = all.filter((a) => a.pipeline_stage === 'Needs Review' && a.evaluation_status === 'Completed');
  const bulkActive = bulkStartedAt !== null;

  // Stop polling once a bulk run has settled (nothing waiting, nothing running).
  const summarized = useRef(false);
  useEffect(() => {
    if (bulkStartedAt === null) {
      summarized.current = false;
      return;
    }
    const fresh = dataUpdatedAt > bulkStartedAt;
    const settled = fresh && notEvaluated === 0 && evaluating === 0;
    const timedOut = Date.now() - bulkStartedAt > BULK_POLL_LIMIT_MS;
    if ((settled || timedOut) && !summarized.current) {
      summarized.current = true;
      setBulkStartedAt(null);
      if (failed > 0) toast.push('error', `Evaluation finished. ${failed} candidate${failed === 1 ? '' : 's'} could not be evaluated.`);
      else toast.push('success', 'All candidates have been evaluated.');
    }
  }, [bulkStartedAt, dataUpdatedAt, notEvaluated, evaluating, failed, toast]);

  const bulkMutation = useMutation({
    mutationFn: () => triggerBulkEvaluation(id),
    onSuccess: () => {
      setBulkStartedAt(Date.now());
      queryClient.invalidateQueries({ queryKey: ['job-applications', id] });
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const evalMutation = useMutation({
    mutationFn: (applicationId: string) => {
      setEvaluatingId(applicationId);
      return evaluateApplication(applicationId);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job-applications', id] }),
    onError: (err) => {
      toast.push('error', describeError(err).message);
      queryClient.invalidateQueries({ queryKey: ['job-applications', id] });
    },
    onSettled: () => setEvaluatingId(null),
  });

  if (jobQuery.isLoading) return <LoadingState label="Loading job…" />;
  if (jobQuery.isError || !jobQuery.data) {
    return <PageError message={describeError(jobQuery.error).message || "We couldn't find that job."} />;
  }
  const job = jobQuery.data;

  return (
    <div>
      <Breadcrumbs items={[{ label: 'Jobs', to: '/jobs' }, { label: job.title }]} />
      <PageHeader
        title={job.title}
        subtitle={`${job.department} · ${job.location} · ${job.employment_type}`}
        actions={
          <>
            <Button variant="secondary" icon={<FileText className="h-3.5 w-3.5" />} onClick={() => setShowDescription((s) => !s)}>
              Job Description
            </Button>
            <Button
              variant="primary"
              icon={<PlayCircle className="h-3.5 w-3.5" />}
              loading={bulkMutation.isPending || bulkActive}
              disabled={notEvaluated === 0 && !bulkActive}
              title={notEvaluated === 0 && !bulkActive ? 'Every candidate has already been evaluated' : undefined}
              onClick={() => bulkMutation.mutate()}
            >
              {bulkActive ? 'Evaluating…' : 'Evaluate All Candidates'}
            </Button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="brand">{job.evaluation_status}</Badge>
        <Badge tone="neutral">
          {isLoading ? 'Loading candidates…' : `${all.length} candidate${all.length === 1 ? '' : 's'}`}
        </Badge>
      </div>

      {showDescription && (
        <SectionCard title="Job description" className="mb-5">
          <p className="whitespace-pre-wrap text-sm text-ink-soft">{job.job_description_text}</p>
          {asList(job.required_skills).length > 0 && (
            <div className="mt-3">
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-faint">Required skills</p>
              <div className="flex flex-wrap gap-1.5">
                {asList(job.required_skills).map((s) => (
                  <Badge key={s} tone="neutral">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </SectionCard>
      )}

      {bulkActive && (
        <div className="mb-5">
          <Notice>
            Evaluating candidates… {completed} of {all.length} evaluated
            {evaluating > 0 ? ` · ${evaluating} in progress` : ''}
            {failed > 0 ? ` · ${failed} failed` : ''}. This page updates automatically.
          </Notice>
        </div>
      )}
      {!bulkActive && failed > 0 && (
        <div className="mb-5">
          <Notice tone="warning">
            {failed} evaluation{failed === 1 ? '' : 's'} didn't finish. Use Retry next to the candidate to run{' '}
            {failed === 1 ? 'it' : 'them'} again.
          </Notice>
        </div>
      )}

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      <div className="pt-5">
        {isLoading ? (
          <LoadingState label="Loading candidates…" />
        ) : isError ? (
          <div className="space-y-3">
            <PageError message={describeError(error).message} />
            <div className="text-center">
              <Button variant="secondary" onClick={refetch}>
                Try again
              </Button>
            </div>
          </div>
        ) : (
          <>
            {tab === 'candidates' && (
              <SectionCard>
                {all.length === 0 ? (
                  <EmptyState title="No candidates yet" description="Candidates who apply for this job will appear here." />
                ) : (
                  <CandidateTable
                    applications={all}
                    evaluatingId={evaluatingId}
                    onEvaluate={(applicationId) => evalMutation.mutate(applicationId)}
                  />
                )}
              </SectionCard>
            )}

            {tab === 'evaluation-results' && (
              <SectionCard>
                {all.length === 0 ? (
                  <EmptyState title="No candidates yet" description="Evaluation results will appear once candidates apply." />
                ) : (
                  <EvaluationResultsTable applications={all} />
                )}
              </SectionCard>
            )}

            {tab === 'recruiter-review' && (
              <SectionCard
                title={`${waitingForReview.length} waiting for your review`}
                action={
                  <Button size="sm" variant="secondary" onClick={() => navigate('/human-review')}>
                    Open Recruiter Review
                  </Button>
                }
              >
                {waitingForReview.length === 0 ? (
                  <EmptyState title="Nothing waiting on you" description="Evaluated candidates who need a decision appear here." />
                ) : (
                  <CandidateTable applications={waitingForReview} />
                )}
              </SectionCard>
            )}

            {tab === 'job-details' && (
              <SectionCard title="Job details">
                <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <Detail label="Title" value={job.title} />
                  <Detail label="Department" value={job.department} />
                  <Detail label="Location" value={job.location} />
                  <Detail label="Employment type" value={job.employment_type} />
                  <Detail label="Status" value={job.evaluation_status} />
                </dl>
                <p className="mb-1 mt-5 text-xs font-semibold uppercase tracking-wider text-ink-faint">Description</p>
                <p className="whitespace-pre-wrap text-sm text-ink-soft">{job.job_description_text}</p>
              </SectionCard>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wider text-ink-faint">{label}</dt>
      <dd className="mt-0.5 text-ink">{value || '—'}</dd>
    </div>
  );
}
