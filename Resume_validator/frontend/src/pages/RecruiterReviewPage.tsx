import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listFollowupActivity } from '../api/followups';
import { useAllApplications, type FlatApplication } from '../hooks/useAllApplications';
import {
  Avatar,
  Breadcrumbs,
  Button,
  EmptyState,
  EvalStatusBadge,
  LoadingState,
  PageError,
  PageHeader,
  ScorePill,
  SectionCard,
  StageBadge,
} from '../components/Primitives';
import { PartialDataNotice } from '../components/PartialDataNotice';

type Filter = 'all' | 'needs-review' | 'shortlisted' | 'follow-up';

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'needs-review', label: 'Needs Review' },
  { id: 'shortlisted', label: 'Shortlisted' },
  { id: 'follow-up', label: 'Follow-up' },
];

const EMPTY_COPY: Record<Filter, { title: string; description: string }> = {
  all: { title: 'Nothing needs your attention', description: 'Evaluated candidates who need a decision will appear here.' },
  'needs-review': { title: 'No candidates need review', description: 'Candidates the AI flags for your judgement appear here.' },
  shortlisted: { title: 'No shortlisted candidates', description: 'Strong matches ready for an interview appear here.' },
  'follow-up': { title: 'No follow-ups in progress', description: 'Candidates you ask for more details appear here.' },
};

export function RecruiterReviewPage() {
  const navigate = useNavigate();
  const { flat, isLoading, isError, partial } = useAllApplications();
  const [filter, setFilter] = useState<Filter>('all');

  const followupIds = useMemo(() => new Set(listFollowupActivity().map((f) => f.applicationId)), []);

  const groups = useMemo(() => {
    const evaluated = flat.filter((a) => a.evaluation_status === 'Completed');
    const needsReview = evaluated.filter((a) => a.pipeline_stage === 'Needs Review');
    const shortlisted = evaluated.filter((a) => a.pipeline_stage === 'Shortlisted');
    const followUp = flat.filter((a) => followupIds.has(a.application_id) && a.pipeline_stage !== 'Rejected');
    const all = new Map<string, FlatApplication>();
    [...needsReview, ...shortlisted, ...followUp].forEach((a) => all.set(a.application_id, a));
    return { all: [...all.values()], needsReview, shortlisted, followUp };
  }, [flat, followupIds]);

  if (isLoading) return <LoadingState label="Loading candidates…" />;
  if (isError) return <PageError message="We couldn't load your candidates. Please try again." />;

  const byFilter: Record<Filter, FlatApplication[]> = {
    all: groups.all,
    'needs-review': groups.needsReview,
    shortlisted: groups.shortlisted,
    'follow-up': groups.followUp,
  };
  const rows = byFilter[filter].slice().sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1));

  return (
    <div>
      <Breadcrumbs items={[{ label: 'Recruiter Review' }]} />
      <PageHeader
        title="Recruiter Review"
        subtitle="Candidates the AI has evaluated that are waiting on your decision."
      />

      <PartialDataNotice show={partial} />

      <div className="mb-4 flex flex-wrap gap-1.5" role="tablist" aria-label="Filter candidates">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`focus-ring inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${
              filter === f.id ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-line text-ink-soft hover:bg-slate-50'
            }`}
          >
            {f.label}
            <span className="text-xs text-ink-faint">{byFilter[f.id].length}</span>
          </button>
        ))}
      </div>

      <SectionCard>
        {rows.length === 0 ? (
          <EmptyState title={EMPTY_COPY[filter].title} description={EMPTY_COPY[filter].description} />
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs font-medium uppercase tracking-wide text-ink-faint">
                  <th className="py-2.5 pr-3 font-medium">Candidate</th>
                  <th className="px-3 py-2.5 font-medium">Job</th>
                  <th className="px-3 py-2.5 font-medium">Score</th>
                  <th className="px-3 py-2.5 font-medium">Stage</th>
                  <th className="px-3 py-2.5 font-medium">Evaluation Status</th>
                  <th className="py-2.5 pl-3 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((a) => (
                  <tr key={a.application_id} className="hover:bg-slate-50/70">
                    <td className="py-3 pr-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={a.candidate_name} size={30} />
                        <div>
                          <p className="font-medium text-ink">{a.candidate_name}</p>
                          <p className="text-xs text-ink-faint">{a.candidate_email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-ink-soft">{a.jobTitle}</td>
                    <td className="px-3 py-3">
                      <ScorePill score={a.overall_score} />
                    </td>
                    <td className="px-3 py-3">
                      <StageBadge stage={a.pipeline_stage} />
                    </td>
                    <td className="px-3 py-3">
                      <EvalStatusBadge status={a.evaluation_status} />
                    </td>
                    <td className="py-3 pl-3 text-right">
                      <Button size="sm" variant="primary" onClick={() => navigate(`/applications/${a.application_id}`, { state: { from: 'review' } })}>
                        Review
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
