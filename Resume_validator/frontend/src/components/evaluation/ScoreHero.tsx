import { PlayCircle } from 'lucide-react';
import type { ApplicationRead } from '../../types';
import { Button, Card, EvalStatusBadge, ScoreRing, StageBadge } from '../Primitives';

/** The visual anchor of the candidate page: the AI score plus where the candidate stands. */
export function ScoreHero({
  application,
  onRunEvaluation,
  running = false,
}: {
  application: ApplicationRead;
  onRunEvaluation?: () => void;
  running?: boolean;
}) {
  const status = application.evaluation_status;
  const evaluated = status === 'Completed';
  const evaluating = status === 'Running' || running;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-5">
        <ScoreRing score={application.overall_score} size={116} />

        <div className="min-w-[220px] flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-faint">AI match score</p>
          <p className="mt-1 text-3xl font-semibold leading-none text-ink">
            {application.overall_score == null ? '—' : Math.round(application.overall_score)}
            <span className="ml-1 text-base font-medium text-ink-faint">/ 100</span>
          </p>
          <p className="mt-2 max-w-md text-sm text-ink-soft">
            {evaluated
              ? 'AI evidence to support your review. It is not a hiring decision.'
              : evaluating
                ? 'Evaluating this candidate against the job requirements…'
                : status === 'Failed'
                  ? "The evaluation didn't finish. Run it again to see the evidence."
                  : 'Run an evaluation to see how this candidate matches the job.'}
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:min-w-[180px]">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-faint">Evaluation status</p>
            <EvalStatusBadge status={status} />
          </div>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-ink-faint">Pipeline stage</p>
            <StageBadge stage={application.pipeline_stage} />
          </div>
        </div>
      </div>

      {onRunEvaluation && (
        <div className="mt-5 flex justify-end border-t border-line pt-4">
          <Button
            size="sm"
            variant={evaluated ? 'ghost' : 'primary'}
            icon={<PlayCircle className="h-3.5 w-3.5" />}
            loading={evaluating}
            onClick={onRunEvaluation}
          >
            {evaluated ? 'Re-run evaluation' : status === 'Failed' ? 'Retry evaluation' : 'Run evaluation'}
          </Button>
        </div>
      )}
    </Card>
  );
}
