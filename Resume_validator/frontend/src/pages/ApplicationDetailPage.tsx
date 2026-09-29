import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useParams } from 'react-router-dom';
import { CalendarClock, FileText, Video } from 'lucide-react';
import { evaluateApplication, getApplication } from '../api/applications';
import { type CachedInterview, getCachedInterview } from '../api/interviews';
import type { ReviewResponse, WorkflowState } from '../types';
import { useAllApplications } from '../hooks/useAllApplications';
import {
  AiSummary,
  ClarifyCard,
  ExperienceCard,
  ResponsibilitiesCard,
  ScoreBreakdownCard,
  SkillsCard,
  StrengthsCard,
  extractEvaluation,
} from '../components/evaluation/EvaluationSections';
import { ScoreHero } from '../components/evaluation/ScoreHero';
import { ReviewFlow } from '../components/evaluation/ReviewFlow';
import { RecruiterActionBar, type ActionMode } from '../components/review/RecruiterActionBar';
import { FollowupCard } from '../components/review/FollowupReplyPanel';
import { useToast } from '../components/Toast';
import { describeError } from '../lib/errors';
import { formatDateTime } from '../lib/format';
import { Avatar, Badge, Breadcrumbs, LoadingState, PageError, SectionCard } from '../components/Primitives';

function InterviewCard({ interview }: { interview: CachedInterview | null }) {
  return (
    <SectionCard title="Interview">
      {!interview ? (
        <p className="text-sm text-ink-soft">
          No interview scheduled. Use <span className="font-medium text-ink">Schedule Interview</span> above and
          tell us when you'd like it.
        </p>
      ) : (
        <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-ink-faint">
              <CalendarClock className="h-3.5 w-3.5" /> When
            </dt>
            <dd className="mt-0.5 font-medium text-ink">{formatDateTime(interview.scheduledAt)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-ink-faint">Duration</dt>
            <dd className="mt-0.5 font-medium text-ink">{interview.durationMinutes} minutes</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-ink-faint">Status</dt>
            <dd className="mt-0.5">
              <Badge tone="brand">{interview.status.replace(/([a-z])([A-Z])/g, '$1 $2')}</Badge>
            </dd>
          </div>
          {interview.candidateResponse && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-ink-faint">Candidate response</dt>
              <dd className="mt-0.5">
                <Badge tone={interview.candidateResponse === 'ACCEPTED' ? 'success' : 'danger'}>
                  {interview.candidateResponse === 'ACCEPTED' ? 'Accepted' : 'Declined'}
                </Badge>
              </dd>
            </div>
          )}
          {interview.meetingUrl && (
            <div className="sm:col-span-2">
              <dt className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-ink-faint">
                <Video className="h-3.5 w-3.5" /> Meeting link
              </dt>
              <dd className="mt-0.5 break-all">
                <a href={interview.meetingUrl} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">
                  {interview.meetingUrl}
                </a>
              </dd>
            </div>
          )}
        </dl>
      )}
    </SectionCard>
  );
}

export function ApplicationDetailPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const fromReview = (useLocation().state as { from?: string } | null)?.from === 'review';
  const toast = useToast();
  const queryClient = useQueryClient();
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [mode, setMode] = useState<ActionMode>(null);
  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  const [interviewVersion, setInterviewVersion] = useState(0);
  const { flat } = useAllApplications();

  const query = useQuery({
    queryKey: ['application', applicationId],
    queryFn: () => getApplication(applicationId as string),
    enabled: Boolean(applicationId),
    // Keep refreshing while an evaluation is running so the page updates itself.
    refetchInterval: (q) => (q.state.data?.evaluation_status === 'Running' ? 2500 : false),
  });

  const evalMutation = useMutation({
    mutationFn: () => evaluateApplication(applicationId as string),
    onSuccess: () => {
      toast.push('success', 'Evaluation completed.');
      queryClient.invalidateQueries({ queryKey: ['application', applicationId] });
      queryClient.invalidateQueries({ queryKey: ['job-applications'] });
    },
    onError: (err) => {
      toast.push('error', describeError(err).message);
      queryClient.invalidateQueries({ queryKey: ['application', applicationId] });
    },
  });

  const app = query.data;
  const data = useMemo(() => (app ? extractEvaluation(app) : null), [app]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const interview = useMemo(() => (app ? getCachedInterview(app.application_id) : null), [app, interviewVersion]);

  if (query.isLoading) return <LoadingState label="Loading candidate…" />;
  if (query.isError || !app || !data) {
    return <PageError message={describeError(query.error).message || "We couldn't find that candidate."} />;
  }

  const listed = flat.find((a) => a.application_id === app.application_id);
  const jobTitle = listed?.jobTitle;
  const jobId = listed?.jobId;
  const resumeName = app.resume_path ? app.resume_path.split(/[\\/]/).pop() : null;

  function askCandidate(topics: string[]) {
    setPrefill(`Ask the candidate about: ${topics.join(', ')}.`);
    setMode('more-details');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  return (
    <div className="mx-auto max-w-4xl">
      <Breadcrumbs
        items={[
          fromReview ? { label: 'Recruiter Review', to: '/human-review' } : { label: 'Candidates', to: '/candidates' },
          ...(jobTitle && jobId ? [{ label: jobTitle, to: `/jobs/${jobId}` }] : []),
          { label: app.candidate_name },
        ]}
      />

      {/* 1. Candidate header */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3.5">
          <Avatar name={app.candidate_name} size={52} />
          <div>
            <h1 className="text-xl font-semibold text-ink">{app.candidate_name}</h1>
            <p className="text-sm text-ink-soft">{app.candidate_email}</p>
            {jobTitle && <p className="mt-0.5 text-xs text-ink-faint">Applied for {jobTitle}</p>}
          </div>
        </div>
        <ReviewFlow evaluationStatus={app.evaluation_status} />
      </div>

      <div className="space-y-5">
        {/* 2. Score + pipeline status */}
        <ScoreHero application={app} running={evalMutation.isPending} onRunEvaluation={() => evalMutation.mutate()} />

        {/* 3. Primary recruiter actions */}
        <RecruiterActionBar
          application={app}
          mode={mode}
          onModeChange={(next) => {
            setMode(next);
            if (next === null) setPrefill(undefined);
          }}
          prefill={prefill}
          onReviewResult={(_result: ReviewResponse, kind) => {
            if (kind === 'schedule') setInterviewVersion((n) => n + 1);
            setPrefill(undefined);
          }}
        />

        {app.recruiter_comments && (
          <div className="rounded-card border border-line bg-white px-4 py-3 text-sm text-ink-soft">
            <span className="font-medium text-ink">Your notes: </span>
            {app.recruiter_comments}
          </div>
        )}

        {/* 4-10. Evaluation evidence */}
        <AiSummary application={app} data={data} workflowState={workflowState} />
        <ScoreBreakdownCard data={data} />
        <SkillsCard data={data} />
        <ResponsibilitiesCard data={data} />
        <ExperienceCard data={data} />
        <StrengthsCard data={data} />
        <ClarifyCard data={data} canAsk={Boolean(app.thread_id)} onAskCandidate={askCandidate} />

        {/* 11. Follow-up */}
        <FollowupCard application={app} onResult={(result) => setWorkflowState(result.workflow_state)} />

        {/* 12. Interview */}
        <InterviewCard interview={interview} />

        {/* 13. Resume */}
        <SectionCard title="Resume">
          {resumeName ? (
            <div className="flex items-center gap-2.5 text-sm text-ink">
              <FileText className="h-4 w-4 text-ink-faint" />
              <span className="font-medium">{resumeName}</span>
            </div>
          ) : (
            <p className="text-sm text-ink-faint">No resume on file.</p>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
