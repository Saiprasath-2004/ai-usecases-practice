import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { createBlock, createFullDayBlock, deleteBlock, listBlocks } from '../../api/calendar';
import { RECRUITER_ID } from '../../types';
import { formatDateTime, formatDate } from '../../lib/format';
import { Button, EmptyState, LoadingState, PageError, SectionCard } from '../Primitives';
import { useToast } from '../Toast';
import { describeError } from '../../lib/errors';

export function BlockEditor() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [adding, setAdding] = useState<'none' | 'range' | 'full-day'>('none');
  const [date, setDate] = useState('');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('10:00');
  const [reason, setReason] = useState('');

  const query = useQuery({
    queryKey: ['calendar-blocks', RECRUITER_ID],
    queryFn: () => listBlocks(RECRUITER_ID),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['calendar-blocks', RECRUITER_ID] });
  }

  function resetForm() {
    setAdding('none');
    setDate('');
    setReason('');
  }

  const createRangeMutation = useMutation({
    mutationFn: () =>
      createBlock({
        recruiter_id: RECRUITER_ID,
        start_at: `${date}T${startTime}:00`,
        end_at: `${date}T${endTime}:00`,
        all_day: false,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      toast.push('success', 'Block added.');
      resetForm();
      invalidate();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const createFullDayMutation = useMutation({
    mutationFn: () =>
      createFullDayBlock({ recruiter_id: RECRUITER_ID, target_date: date, reason: reason || undefined }),
    onSuccess: () => {
      toast.push('success', 'Full-day block added.');
      resetForm();
      invalidate();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteBlock(id),
    onSuccess: () => {
      toast.push('success', 'Block removed.');
      invalidate();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  if (query.isLoading) return <LoadingState label="Loading blocked periods…" />;
  if (query.isError) return <PageError message={describeError(query.error).message} />;

  const blocks = query.data ?? [];

  return (
    <SectionCard
      title="Blocked periods"
      action={
        adding === 'none' && (
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setAdding('range')}>
              Block time range
            </Button>
            <Button size="sm" variant="ghost" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setAdding('full-day')}>
              Block full day
            </Button>
          </div>
        )
      }
    >
      {adding !== 'none' && (
        <div className="mb-4 space-y-2 rounded-md border border-line bg-slate-50/60 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
            />
            {adding === 'range' && (
              <>
                <input
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
                />
                <span className="text-ink-faint">–</span>
                <input
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
                />
              </>
            )}
          </div>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (optional)"
            className="focus-ring h-8 w-full rounded-md border border-line px-2.5 text-sm placeholder:text-ink-faint"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="primary"
              disabled={!date}
              loading={createRangeMutation.isPending || createFullDayMutation.isPending}
              onClick={() => (adding === 'range' ? createRangeMutation.mutate() : createFullDayMutation.mutate())}
            >
              Save block
            </Button>
            <Button size="sm" variant="ghost" onClick={resetForm}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {blocks.length === 0 ? (
        <EmptyState title="No blocked periods" description="Time off, holidays, or other unavailable windows will show here." />
      ) : (
        <ul className="divide-y divide-line-soft">
          {blocks.map((b) => (
            <li key={b.id} className="flex items-center justify-between py-2.5 text-sm">
              <div>
                <span className="font-medium text-ink">
                  {b.all_day ? formatDate(b.start_at) : formatDateTime(b.start_at)}
                </span>
                {!b.all_day && <span className="text-ink-soft"> – {formatDateTime(b.end_at)}</span>}
                {b.reason && <span className="ml-2 text-ink-faint">({b.reason})</span>}
              </div>
              <button
                className="focus-ring text-ink-faint hover:text-danger-600"
                onClick={() => b.id && deleteMutation.mutate(b.id)}
                aria-label="Remove block"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
