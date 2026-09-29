import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarClock } from 'lucide-react';
import {
  type CachedInterview,
  listCachedInterviews,
  updateCachedInterviewResponse,
} from '../api/interviews';
import { respondToInterview } from '../api/applications';
import { useToast } from '../components/Toast';
import { describeError } from '../lib/errors';
import { formatDateTime } from '../lib/format';
import { Badge, Button, EmptyState, PageHeader, SectionCard } from '../components/Primitives';

type Filter = 'all' | 'today' | 'tomorrow' | 'week' | 'upcoming' | 'accepted' | 'awaiting' | 'declined';

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'today', label: 'Today' },
  { id: 'tomorrow', label: 'Tomorrow' },
  { id: 'week', label: 'This Week' },
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'awaiting', label: 'Awaiting Response' },
  { id: 'declined', label: 'Declined' },
];

function isSameDay(a: Date, b: Date) {
  return a.toDateString() === b.toDateString();
}

function matchesFilter(interview: CachedInterview, filter: Filter): boolean {
  const scheduled = new Date(interview.scheduledAt);
  const now = new Date();
  switch (filter) {
    case 'today':
      return isSameDay(scheduled, now);
    case 'tomorrow': {
      const tomorrow = new Date(now);
      tomorrow.setDate(now.getDate() + 1);
      return isSameDay(scheduled, tomorrow);
    }
    case 'week': {
      const weekOut = new Date(now);
      weekOut.setDate(now.getDate() + 7);
      return scheduled >= now && scheduled <= weekOut;
    }
    case 'upcoming':
      return scheduled.getTime() > now.getTime();
    case 'accepted':
      return interview.candidateResponse === 'ACCEPTED';
    case 'awaiting':
      return !interview.candidateResponse;
    case 'declined':
      return interview.candidateResponse === 'DECLINED';
    default:
      return true;
  }
}

export function InterviewsPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const toast = useToast();
  const queryClient = useQueryClient();
  const interviews = listCachedInterviews().filter((i) => matchesFilter(i, filter));

  const respondMutation = useMutation({
    mutationFn: ({ applicationId, response }: { applicationId: string; response: 'ACCEPTED' | 'DECLINED' }) =>
      respondToInterview(applicationId, { response }),
    onSuccess: (result) => {
      updateCachedInterviewResponse(
        result.application_id,
        result.interview.invitation_status,
        result.interview.candidate_response,
      );
      toast.push('success', `Recorded candidate response: ${result.interview.candidate_response}.`);
      queryClient.invalidateQueries({ queryKey: ['application', result.application_id] });
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  return (
    <div>
      <PageHeader title="Interviews" subtitle="Interviews you have scheduled with candidates." />


      <div className="mb-4 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`focus-ring rounded-full border px-3 py-1 text-xs font-medium ${
              filter === f.id ? 'border-brand-600 bg-brand-50 text-brand-700' : 'border-line text-ink-soft hover:bg-slate-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <SectionCard>
        {interviews.length === 0 ? (
          <EmptyState
            icon={<CalendarClock className="h-5 w-5" />}
            title="No interviews to show"
            description="Use Schedule Interview on a candidate's page to book one."
          />
        ) : (
          <div className="divide-y divide-line">
            {interviews.map((i) => (
              <div key={i.applicationId} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium text-ink">{i.candidateEmail}</p>
                  <p className="text-xs text-ink-faint">{formatDateTime(i.scheduledAt)} · {i.durationMinutes} min</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{i.status.replace(/([a-z])([A-Z])/g, '$1 $2')}</Badge>
                  {i.candidateResponse ? (
                    <Badge tone={i.candidateResponse === 'ACCEPTED' ? 'success' : 'danger'}>
                      {i.candidateResponse}
                    </Badge>
                  ) : (
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={respondMutation.isPending}
                        onClick={() => respondMutation.mutate({ applicationId: i.applicationId, response: 'ACCEPTED' })}
                      >
                        Mark accepted
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={respondMutation.isPending}
                        onClick={() => respondMutation.mutate({ applicationId: i.applicationId, response: 'DECLINED' })}
                      >
                        Mark declined
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
