import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAllApplications } from '../hooks/useAllApplications';
import { PIPELINE_STAGES } from '../types';
import { CandidateTable } from '../components/candidates/CandidateTable';
import { EmptyState, LoadingState, PageError, PageHeader, SectionCard } from '../components/Primitives';
import { PartialDataNotice } from '../components/PartialDataNotice';

export function CandidatesPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get('q') ?? '';
  const [stage, setStage] = useState<string>('all');
  const { jobs, flat, isLoading, isError, partial } = useAllApplications();

  const filtered = useMemo(() => {
    return flat.filter((a) => {
      const matchesQuery =
        !query ||
        a.candidate_name.toLowerCase().includes(query.toLowerCase()) ||
        a.candidate_email.toLowerCase().includes(query.toLowerCase()) ||
        a.jobTitle.toLowerCase().includes(query.toLowerCase());
      const matchesStage = stage === 'all' || a.pipeline_stage === stage;
      return matchesQuery && matchesStage;
    });
  }, [flat, query, stage]);

  if (isLoading) return <LoadingState label="Loading candidates…" />;
  if (isError) return <PageError message="Couldn't load candidates from one or more jobs." />;

  const jobTitleFor = (applicationId: string) => flat.find((a) => a.application_id === applicationId)?.jobTitle;

  return (
    <div>
      <PageHeader title="Candidates" subtitle={`${flat.length} candidates across ${jobs.length} job${jobs.length === 1 ? '' : 's'}`} />

      <PartialDataNotice show={partial} />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setParams(e.target.value ? { q: e.target.value } : {})}
          placeholder="Search by name, email, or job…"
          className="input max-w-xs"
        />
        <select value={stage} onChange={(e) => setStage(e.target.value)} className="input w-auto">
          <option value="all">All stages</option>
          {PIPELINE_STAGES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <SectionCard>
        {filtered.length === 0 ? (
          <EmptyState title="No candidates match" description="Try a different search term or stage filter." />
        ) : (
          <CandidateTable applications={filtered} showJobColumn jobTitleFor={jobTitleFor} />
        )}
      </SectionCard>
    </div>
  );
}
