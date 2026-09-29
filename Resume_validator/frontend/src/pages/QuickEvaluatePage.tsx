import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ExternalLink, PlayCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAllApplications } from '../hooks/useAllApplications';
import { evaluateApplication } from '../api/applications';
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
import { useToast } from '../components/Toast';
import { describeError } from '../lib/errors';
import { Button, EmptyState, LoadingState, PageError, PageHeader, SectionCard } from '../components/Primitives';

export function QuickEvaluatePage() {
  const { flat, isLoading, isError } = useAllApplications();
  const [selectedId, setSelectedId] = useState<string>('');
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const selected = useMemo(() => flat.find((a) => a.application_id === selectedId) ?? null, [flat, selectedId]);

  const evalMutation = useMutation({
    mutationFn: () => evaluateApplication(selectedId),
    onSuccess: () => {
      toast.push('success', 'Evaluation completed.');
      queryClient.invalidateQueries({ queryKey: ['job-applications'] });
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  if (isLoading) return <LoadingState label="Loading candidates…" />;
  if (isError) return <PageError message="Couldn't load one or more jobs' candidates." />;

  return (
    <div>
      <PageHeader title="Quick Evaluate" subtitle="Pick a candidate and run their evaluation right away." />

      <SectionCard className="mb-5">
        {flat.length === 0 ? (
          <EmptyState title="No applications yet" description="Create a job and add candidates before evaluating." />
        ) : (
          <div className="flex flex-wrap items-end gap-3">
            <label className="block w-72 text-xs font-medium text-ink-soft">
              Candidate
              <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} className="input mt-1">
                <option value="">Select a candidate…</option>
                {flat.map((a) => (
                  <option key={a.application_id} value={a.application_id}>
                    {a.candidate_name} — {a.jobTitle}
                  </option>
                ))}
              </select>
            </label>
            <Button
              variant="primary"
              icon={<PlayCircle className="h-3.5 w-3.5" />}
              disabled={!selectedId}
              loading={evalMutation.isPending}
              onClick={() => evalMutation.mutate()}
            >
              {selected?.evaluation_status === 'Completed' ? 'Re-run evaluation' : 'Run evaluation'}
            </Button>
          </div>
        )}
      </SectionCard>

      {selected && (
        <div className="space-y-5">
          <ScoreHero application={selected} />
          <AiSummary application={selected} data={extractEvaluation(selected)} />
          <ScoreBreakdownCard data={extractEvaluation(selected)} />
          <SkillsCard data={extractEvaluation(selected)} />
          <ResponsibilitiesCard data={extractEvaluation(selected)} />
          <ExperienceCard data={extractEvaluation(selected)} />
          <StrengthsCard data={extractEvaluation(selected)} />
          <ClarifyCard data={extractEvaluation(selected)} canAsk={false} />
          <div className="text-right">
            <Button
              variant="primary"
              icon={<ExternalLink className="h-3.5 w-3.5" />}
              onClick={() => navigate(`/applications/${selected.application_id}`)}
            >
              Open candidate to make a decision
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
