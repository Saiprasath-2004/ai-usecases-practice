import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Send } from 'lucide-react';
import { submitFollowupReply } from '../../api/applications';
import { getFollowupActivity, recordFollowupReplied } from '../../api/followups';
import type { ApplicationRead, FollowupReplyResponse } from '../../types';
import { formatDateTime } from '../../lib/format';
import { Badge, Button, ScorePill, SectionCard } from '../Primitives';
import { useToast } from '../Toast';
import { describeError } from '../../lib/errors';

/** Follow-up: what was asked, and a place to record the candidate's reply. */
export function FollowupCard({
  application,
  onResult,
}: {
  application: ApplicationRead;
  onResult?: (result: FollowupReplyResponse) => void;
}) {
  const [reply, setReply] = useState('');
  const [comparison, setComparison] = useState<{ before: number | null; after: number | null } | null>(null);
  const [, bump] = useState(0);
  const toast = useToast();
  const queryClient = useQueryClient();
  const activity = getFollowupActivity(application.application_id);

  const mutation = useMutation({
    mutationFn: () => submitFollowupReply(application.application_id, { candidate_reply: reply }),
    onSuccess: (result) => {
      setComparison({ before: application.overall_score, after: result.overall_score });
      recordFollowupReplied(application.application_id);
      bump((n) => n + 1);
      toast.push('success', "Reply recorded. The candidate's evaluation has been updated.");
      onResult?.(result);
      setReply('');
      queryClient.invalidateQueries({ queryKey: ['application', application.application_id] });
      queryClient.invalidateQueries({ queryKey: ['job-applications'] });
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const hasThread = Boolean(application.thread_id);
  const replied = Boolean(activity?.repliedAt);

  return (
    <SectionCard
      title="Follow-up"
      action={
        activity ? (
          <Badge tone={replied ? 'success' : 'brand'}>{replied ? 'Candidate replied' : 'Awaiting reply'}</Badge>
        ) : undefined
      }
    >
      {activity ? (
        <p className="mb-3 text-sm text-ink-soft">
          Additional information requested on {formatDateTime(activity.requestedAt)}.
          {replied && activity.repliedAt ? ` Reply recorded ${formatDateTime(activity.repliedAt)}.` : ''}
        </p>
      ) : (
        <p className="mb-3 text-sm text-ink-soft">
          You haven't asked this candidate for more details. Use <span className="font-medium text-ink">Get More Details</span>{' '}
          above to send questions about the areas to clarify.
        </p>
      )}

      {!hasThread ? (
        <p className="text-sm text-ink-faint">Run an evaluation first to enable follow-up.</p>
      ) : (
        <>
          <label htmlFor="candidate-reply" className="mb-1.5 block text-sm font-medium text-ink">
            Candidate's reply
          </label>
          <textarea
            id="candidate-reply"
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            rows={3}
            placeholder="Paste or type what the candidate wrote back…"
            className="input"
          />
          <Button
            className="mt-2"
            variant="primary"
            size="sm"
            icon={<Send className="h-3.5 w-3.5" />}
            loading={mutation.isPending}
            disabled={!reply.trim()}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? 'Updating evaluation…' : 'Record reply & update evaluation'}
          </Button>

          {comparison && (
            <div className="mt-3 flex items-center gap-2 rounded-md bg-brand-50 px-3 py-2 text-sm">
              <span className="text-ink-soft">Score:</span>
              <ScorePill score={comparison.before} />
              <ArrowRight className="h-3.5 w-3.5 text-ink-faint" />
              <ScorePill score={comparison.after} />
            </div>
          )}
        </>
      )}
    </SectionCard>
  );
}
