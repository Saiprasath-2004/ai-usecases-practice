import { useAllApplications } from '../hooks/useAllApplications';
import { LoadingState, PageError, PageHeader, SectionCard, StageBadge } from '../components/Primitives';
import { PIPELINE_STAGES } from '../types';
import { PartialDataNotice } from '../components/PartialDataNotice';

const SCORE_BUCKETS = [
  { label: '0–20', min: 0, max: 20 },
  { label: '21–40', min: 21, max: 40 },
  { label: '41–60', min: 41, max: 60 },
  { label: '61–80', min: 61, max: 80 },
  { label: '81–100', min: 81, max: 100 },
];

function Bar({ label, count, total, tone = 'bg-brand-500' }: { label: string; count: number; total: number; tone?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 truncate text-sm text-ink-soft">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${total ? (count / total) * 100 : 0}%` }} />
      </div>
      <span className="w-6 text-right text-sm text-ink-soft">{count}</span>
    </div>
  );
}

export function AnalyticsPage() {
  const { jobs, flat, isLoading, isError, partial } = useAllApplications();

  if (isLoading) return <LoadingState label="Loading analytics…" />;
  if (isError) return <PageError message="Couldn't load one or more jobs' candidates." />;

  const total = flat.length;
  const evaluated = flat.filter((a) => a.evaluation_status === 'Completed').length;
  const pending = flat.filter((a) => a.evaluation_status === 'Pending').length;
  const running = flat.filter((a) => a.evaluation_status === 'Running').length;
  const failed = flat.filter((a) => a.evaluation_status === 'Failed').length;

  const scored = flat.filter((a) => a.overall_score != null);
  const buckets = SCORE_BUCKETS.map((b) => ({
    ...b,
    count: scored.filter((a) => (a.overall_score as number) >= b.min && (a.overall_score as number) <= b.max).length,
  }));

  const perJob = jobs
    .map((job) => ({ job, count: flat.filter((a) => a.jobId === job.id).length }))
    .sort((a, b) => b.count - a.count);

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Where your candidates stand across every job." />

      <PartialDataNotice show={partial} />

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard title="Candidates by pipeline stage">
          <div className="space-y-2.5">
            {PIPELINE_STAGES.map((stage) => (
              <div key={stage} className="flex items-center gap-3">
                <div className="w-32 shrink-0">
                  <StageBadge stage={stage} />
                </div>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${total ? (flat.filter((a) => a.pipeline_stage === stage).length / total) * 100 : 0}%` }}
                  />
                </div>
                <span className="w-6 text-right text-sm text-ink-soft">
                  {flat.filter((a) => a.pipeline_stage === stage).length}
                </span>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Evaluation status">
          <div className="space-y-2.5">
            <Bar label="Completed" count={evaluated} total={total} tone="bg-success-500" />
            <Bar label="Evaluating" count={running} total={total} tone="bg-brand-500" />
            <Bar label="Not Evaluated" count={pending} total={total} tone="bg-slate-400" />
            <Bar label="Failed" count={failed} total={total} tone="bg-danger-500" />
          </div>
        </SectionCard>

        <SectionCard title="Score distribution">
          {scored.length === 0 ? (
            <p className="text-sm text-ink-faint">No scored candidates yet.</p>
          ) : (
            <div className="space-y-2.5">
              {buckets.map((b) => (
                <Bar key={b.label} label={b.label} count={b.count} total={scored.length} />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Candidates per job">
          {perJob.length === 0 ? (
            <p className="text-sm text-ink-faint">No jobs yet.</p>
          ) : (
            <div className="space-y-2.5">
              {perJob.map(({ job, count }) => (
                <Bar key={job.id} label={job.title} count={count} total={total} />
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
