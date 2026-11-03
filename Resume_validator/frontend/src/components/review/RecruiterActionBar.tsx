import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarPlus, HelpCircle, PauseCircle, RotateCcw, XCircle } from 'lucide-react';
import { holdApplication, moveToReview, rejectApplication, submitReview } from '../../api/applications';
import { cacheInterviewFromInline } from '../../api/interviews';
import { recordFollowupRequested } from '../../api/followups';
import type { ApplicationRead, ReviewResponse } from '../../types';
import { Button, Card } from '../Primitives';
import { ConfirmDialog } from '../ConfirmDialog';
import { useToast } from '../Toast';
import { describeError } from '../../lib/errors';

export type ActionMode = 'schedule' | 'more-details' | null;

const SCHEDULE_SUGGESTIONS = ['Next Tuesday afternoon', 'Tomorrow at 2 PM', 'Friday between 10 and 12'];

/**
 * The recruiter's decision, always visible near the top of the candidate
 * page. Primary: Schedule Interview. Secondary: Get More Details.
 * Pipeline: Hold / Move to Review. Destructive: Reject.
 */
export function RecruiterActionBar({
  application,
  mode,
  onModeChange,
  prefill,
  onReviewResult,
}: {
  application: ApplicationRead;
  mode: ActionMode;
  onModeChange: (mode: ActionMode) => void;
  prefill?: string;
  onReviewResult?: (result: ReviewResponse, kind: 'schedule' | 'more-details') => void;
}) {
  const [comments, setComments] = useState('');
  const [confirmingReject, setConfirmingReject] = useState(false);
  const toast = useToast();
  const queryClient = useQueryClient();

  useEffect(() => {
    setComments(prefill ?? '');
  }, [prefill, mode]);

  const id = application.application_id;
  const hasThread = Boolean(application.thread_id);
  const busyEvaluating = application.evaluation_status === 'Running';
  const stage = application.pipeline_stage;

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['application', id] });
    queryClient.invalidateQueries({ queryKey: ['job-applications'] });
  }

  const reviewMutation = useMutation({
    mutationFn: (decision: 'Schedule Interview' | 'Get More Details') =>
      submitReview(id, { decision, comments: comments.trim() || undefined }),
    onSuccess: (result, decision) => {
      if (decision === 'Schedule Interview') {
        if (result.interview) cacheInterviewFromInline(result.interview);
        toast.push('success', 'Interview scheduled.');
        onReviewResult?.(result, 'schedule');
      } else {
        recordFollowupRequested(id, result.communication?.status ?? null);
        toast.push('success', 'Follow-up questions sent to the candidate.');
        onReviewResult?.(result, 'more-details');
      }
      onModeChange(null);
      refresh();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const holdMutation = useMutation({
    mutationFn: () => holdApplication(id),
    onSuccess: () => {
      toast.push('success', 'Candidate placed on hold.');
      refresh();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const moveMutation = useMutation({
    mutationFn: () => moveToReview(id),
    onSuccess: () => {
      toast.push('success', 'Candidate moved to Needs Review.');
      refresh();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectApplication(id),
    onSuccess: () => {
      toast.push('success', 'Candidate rejected and notified.');
      setConfirmingReject(false);
      refresh();
    },
    onError: (err) => {
      toast.push('error', describeError(err).message);
      setConfirmingReject(false);
    },
  });

  const needsEvaluation = 'Run an evaluation first';

  return (
    <Card className="p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">Recruiter's Decision</h2>
        <p className="text-xs text-ink-faint">You make the final call on every candidate.</p>
      </div>

      {mode ? (
        <div>
          <label htmlFor="decision-comments" className="mb-1.5 block text-sm font-medium text-ink">
            {mode === 'schedule' ? 'When should the interview happen?' : 'What would you like to ask the candidate?'}
          </label>
          <textarea
            id="decision-comments"
            autoFocus
            rows={3}
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            placeholder={
              mode === 'schedule'
                ? 'e.g. Schedule next Tuesday afternoon.'
                : 'e.g. Ask whether they have experience with Jenkins.'
            }
            className="input"
          />
          {mode === 'schedule' && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SCHEDULE_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setComments(`Schedule ${s.charAt(0).toLowerCase()}${s.slice(1)}.`)}
                  className="focus-ring rounded-full border border-line bg-white px-2.5 py-1 text-xs text-ink-soft hover:bg-slate-50"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          <p className="mt-2 text-xs text-ink-faint">
            {mode === 'schedule'
              ? "Write it in your own words — we'll find an open time on your calendar and invite the candidate."
              : 'We turn your note and the areas to clarify into questions and send them to the candidate.'}
          </p>
          <div className="mt-3 flex gap-2">
            <Button
              variant="primary"
              size="sm"
              loading={reviewMutation.isPending}
              disabled={mode === 'schedule' && !comments.trim()}
              onClick={() => reviewMutation.mutate(mode === 'schedule' ? 'Schedule Interview' : 'Get More Details')}
            >
              {reviewMutation.isPending
                ? mode === 'schedule'
                  ? 'Finding an available time…'
                  : 'Sending…'
                : mode === 'schedule'
                  ? 'Schedule interview'
                  : 'Send questions'}
            </Button>
            <Button variant="ghost" size="sm" disabled={reviewMutation.isPending} onClick={() => onModeChange(null)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            icon={<CalendarPlus className="h-4 w-4" />}
            disabled={!hasThread || busyEvaluating}
            title={!hasThread ? needsEvaluation : undefined}
            onClick={() => onModeChange('schedule')}
          >
            Schedule Interview
          </Button>
          <Button
            variant="secondary"
            icon={<HelpCircle className="h-4 w-4" />}
            disabled={!hasThread || busyEvaluating}
            title={!hasThread ? needsEvaluation : undefined}
            onClick={() => onModeChange('more-details')}
          >
            Get More Details
          </Button>

          <span className="mx-1 hidden h-6 w-px bg-line sm:block" aria-hidden />

          <Button
            variant="secondary"
            icon={<PauseCircle className="h-4 w-4" />}
            loading={holdMutation.isPending}
            disabled={busyEvaluating || stage === 'On Hold'}
            title={stage === 'On Hold' ? 'Already on hold' : undefined}
            onClick={() => holdMutation.mutate()}
          >
            Hold
          </Button>
          <Button
            variant="secondary"
            icon={<RotateCcw className="h-4 w-4" />}
            loading={moveMutation.isPending}
            disabled={busyEvaluating || stage === 'Needs Review'}
            title={stage === 'Needs Review' ? 'Already in Needs Review' : undefined}
            onClick={() => moveMutation.mutate()}
          >
            Move to Review
          </Button>

          <span className="mx-1 hidden h-6 w-px bg-line sm:block" aria-hidden />

          <Button
            variant="danger-outline"
            icon={<XCircle className="h-4 w-4" />}
            disabled={!hasThread || busyEvaluating || stage === 'Rejected'}
            title={stage === 'Rejected' ? 'Already rejected' : !hasThread ? needsEvaluation : undefined}
            onClick={() => setConfirmingReject(true)}
          >
            Reject
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmingReject}
        title="Reject this candidate?"
        description={`${application.candidate_name} will be moved to Rejected and sent a rejection email. Their evaluation stays on record.`}
        confirmLabel="Reject candidate"
        variant="danger"
        loading={rejectMutation.isPending}
        onConfirm={() => rejectMutation.mutate()}
        onCancel={() => setConfirmingReject(false)}
      />
    </Card>
  );
}
