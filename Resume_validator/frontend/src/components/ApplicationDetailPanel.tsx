import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { X, CheckCircle2, PauseCircle, XCircle, RotateCcw, CalendarClock, MailQuestion } from 'lucide-react';
import { getApplication, performAction, approveFollowup, getInterviewSlots, submitFollowupReplyStub } from '../api/applications';
import { ScoreRing, Spinner, StageBadge } from './Primitives';
import { asList, asRecord } from '../lib/format';
import type { ApplicationRead, RecruiterActionType } from '../types';
import { useToast } from './Toast';

export default function ApplicationDetailPanel() {
  const { appId } = useParams();
  const { jobId } = useOutletContext<{ jobId: number }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { push } = useToast();

  const { data: app, isLoading, isError, error } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => getApplication(appId as string),
    enabled: !!appId,
  });

  const close = () => navigate(`/jobs/${jobId}`);

  const action = useMutation({
    mutationFn: (type: RecruiterActionType) => performAction(appId as string, type),
    onSuccess: (res) => {
      push('success', res.message);
      qc.invalidateQueries({ queryKey: ['job-applications', jobId] });
      qc.invalidateQueries({ queryKey: ['application', appId] });
    },
    onError: (err) => push('error', (err as Error).message || 'Action failed.'),
  });

  const stubCall = useMutation({
    mutationFn: (fn: () => Promise<{ status: string; message: string }>) => fn(),
    onSuccess: (res) => push('info', res.message),
    onError: (err) => push('error', (err as Error).message || 'Request failed.'),
  });

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button aria-label="Close panel" onClick={close} className="absolute inset-0 bg-ink/25 backdrop-blur-[1px]" />

      <div className="scrollbar-thin relative flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-line bg-paper shadow-lift">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-paper/95 px-6 py-4 backdrop-blur">
          <p className="font-mono text-[11px] uppercase tracking-wide text-ink-faint">Application detail</p>
          <button onClick={close} className="focus-ring rounded p-1 text-ink-faint hover:text-ink" aria-label="Close">
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        {isLoading && (
          <div className="flex flex-1 items-center justify-center gap-2 text-ink-faint">
            <Spinner className="h-5 w-5" /> Loading candidate…
          </div>
        )}

        {isError && (
          <div className="p-6 text-sm text-rust-600">{(error as Error)?.message || 'Could not load this application.'}</div>
        )}

        {app && (
          <div className="flex-1 px-6 py-6">
            <div className="flex items-start gap-4">
              <ScoreRing score={app.overall_score} size={56} />
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-2xl leading-tight text-ink">{app.candidate_name}</h2>
                <p className="text-sm text-ink-faint">{app.candidate_email}</p>
                <div className="mt-2 flex items-center gap-2">
                  <StageBadge stage={app.pipeline_stage} />
                  <span className="text-xs text-ink-faint">{app.evaluation_status}</span>
                </div>
              </div>
            </div>

            {app.evaluation_verdict && (
              <Section title="Verdict">
                <p className="text-sm leading-relaxed text-ink-soft">{app.evaluation_verdict}</p>
              </Section>
            )}

            <Section title="Resume">
              <p className="break-all font-mono text-xs text-ink-faint">{app.resume_path}</p>
            </Section>

            <SkillsRow app={app} />
            <ResponsibilitiesRow app={app} />

            {app.experience_result && asRecord(app.experience_result) && (
              <Section title="Experience">
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                  {Object.entries(asRecord(app.experience_result) ?? {}).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-ink-faint">{k.replace(/_/g, ' ')}</dt>
                      <dd className="text-ink-soft">{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </Section>
            )}

            {app.recruiter_comments && (
              <Section title="Recruiter notes">
                <p className="text-sm text-ink-soft">{app.recruiter_comments}</p>
              </Section>
            )}

            {!hasEvidence(app) && (
              <div className="mt-6 rounded-card border border-dashed border-line bg-panel/60 px-4 py-3 text-xs leading-relaxed text-ink-faint">
                Score breakdown and evidence aren't showing because the backend's{' '}
                <code className="font-mono">ApplicationRead</code> response model doesn't include those columns yet,
                even though they're stored on the <code className="font-mono">Application</code> table. Add them to{' '}
                <code className="font-mono">api/schemas/applications.py</code> to surface them here.
              </div>
            )}

            <Section title="Recruiter actions">
              <div className="flex flex-wrap gap-2">
                <ActionButton
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  label="Shortlist"
                  tone="moss"
                  disabled={action.isPending}
                  onClick={() => action.mutate('SHORTLIST')}
                />
                <ActionButton
                  icon={<PauseCircle className="h-4 w-4" />}
                  label="Hold"
                  tone="violet"
                  disabled={action.isPending}
                  onClick={() => action.mutate('HOLD')}
                />
                <ActionButton
                  icon={<RotateCcw className="h-4 w-4" />}
                  label="Move to review"
                  tone="amber"
                  disabled={action.isPending}
                  onClick={() => action.mutate('MOVE_TO_REVIEW')}
                />
                <ActionButton
                  icon={<XCircle className="h-4 w-4" />}
                  label="Reject"
                  tone="rust"
                  disabled={action.isPending}
                  onClick={() => action.mutate('REJECT')}
                />
              </div>
            </Section>

            <Section title="Interview & follow-up" hint="These backend routes are stubs today and won't take real effect.">
              <div className="flex flex-wrap gap-2">
                <ActionButton
                  icon={<CalendarClock className="h-4 w-4" />}
                  label="Check interview slots"
                  tone="ink"
                  disabled={stubCall.isPending}
                  onClick={() => stubCall.mutate(() => getInterviewSlots(app.application_id))}
                />
                <ActionButton
                  icon={<MailQuestion className="h-4 w-4" />}
                  label="Approve follow-up"
                  tone="ink"
                  disabled={stubCall.isPending}
                  onClick={() => stubCall.mutate(() => approveFollowup(app.application_id))}
                />
                <ActionButton
                  icon={<MailQuestion className="h-4 w-4" />}
                  label="Log follow-up reply"
                  tone="ink"
                  disabled={stubCall.isPending}
                  onClick={() => stubCall.mutate(() => submitFollowupReplyStub(app.application_id))}
                />
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}

function hasEvidence(app: ApplicationRead) {
  return Boolean(
    app.score_breakdown || app.matched_skills || app.missing_skills || app.strengths || app.gaps
  );
}

function SkillsRow({ app }: { app: ApplicationRead }) {
  const matched = asList(app.matched_skills);
  const missing = asList(app.missing_skills);
  const strengths = asList(app.strengths);
  const gaps = asList(app.gaps);

  if (matched.length + missing.length + strengths.length + gaps.length === 0) return null;

  return (
    <Section title="Skills & fit">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TagGroup label="Matched skills" items={matched} tone="moss" />
        <TagGroup label="Missing skills" items={missing} tone="rust" />
        <TagGroup label="Strengths" items={strengths} tone="moss" />
        <TagGroup label="Gaps" items={gaps} tone="rust" />
      </div>
    </Section>
  );
}

function ResponsibilitiesRow({ app }: { app: ApplicationRead }) {
  const matched = asList(app.responsibilities_matched);
  const missing = asList(app.responsibilities_missing);
  if (matched.length + missing.length === 0) return null;

  return (
    <Section title="Responsibilities">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TagGroup label="Covered" items={matched} tone="moss" />
        <TagGroup label="Not covered" items={missing} tone="rust" />
      </div>
    </Section>
  );
}

function TagGroup({ label, items, tone }: { label: string; items: string[]; tone: 'moss' | 'rust' }) {
  if (items.length === 0) return null;
  const cls = tone === 'moss' ? 'bg-moss-50 text-moss-600' : 'bg-rust-50 text-rust-600';
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-ink-faint">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span key={i} className={`rounded-full px-2.5 py-1 text-xs ${cls}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div className="mt-6 border-t border-line pt-5">
      <div className="mb-2.5 flex items-baseline justify-between">
        <h3 className="font-display text-sm text-ink">{title}</h3>
        {hint && <span className="text-[11px] text-ink-faint">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
  disabled,
  tone,
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone: 'moss' | 'violet' | 'amber' | 'rust' | 'ink';
}) {
  const toneMap: Record<string, string> = {
    moss: 'border-moss-200 text-moss-600 hover:bg-moss-50',
    violet: 'border-violet-200 text-violet-600 hover:bg-violet-50',
    amber: 'border-amber-200 text-amber-600 hover:bg-amber-50',
    rust: 'border-rust-200 text-rust-600 hover:bg-rust-50',
    ink: 'border-line text-ink-soft hover:bg-panel',
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`focus-ring inline-flex items-center gap-1.5 rounded-md border bg-white px-3 py-2 text-xs font-medium transition-colors disabled:opacity-50 ${toneMap[tone]}`}
    >
      {icon}
      {label}
    </button>
  );
}
