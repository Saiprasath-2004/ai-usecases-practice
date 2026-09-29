import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { createAvailability, deleteAvailability, listAvailability, updateAvailability } from '../../api/calendar';
import { RECRUITER_ID, WEEKDAY_LABELS } from '../../types';
import { formatTime } from '../../lib/format';
import { Button, EmptyState, LoadingState, PageError, SectionCard } from '../Primitives';
import { useToast } from '../Toast';
import { describeError } from '../../lib/errors';

export function AvailabilityEditor() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [addingDay, setAddingDay] = useState<number | null>(null);
  const [start, setStart] = useState('09:00');
  const [end, setEnd] = useState('17:00');

  const query = useQuery({
    queryKey: ['availability', RECRUITER_ID],
    queryFn: () => listAvailability(RECRUITER_ID),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['availability', RECRUITER_ID] });
  }

  const createMutation = useMutation({
    mutationFn: () =>
      createAvailability({
        recruiter_id: RECRUITER_ID,
        day_of_week: addingDay as number,
        start_time: `${start}:00`,
        end_time: `${end}:00`,
        active: true,
      }),
    onSuccess: () => {
      toast.push('success', 'Availability window added.');
      setAddingDay(null);
      invalidate();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateAvailability(id, { active }),
    onSuccess: invalidate,
    onError: (err) => toast.push('error', describeError(err).message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAvailability(id),
    onSuccess: () => {
      toast.push('success', 'Availability window removed.');
      invalidate();
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  if (query.isLoading) return <LoadingState label="Loading availability…" />;
  if (query.isError) return <PageError message={describeError(query.error).message} />;

  const byDay = new Map<number, typeof query.data>();
  (query.data ?? []).forEach((w) => {
    byDay.set(w.day_of_week, [...(byDay.get(w.day_of_week) ?? []), w]);
  });

  return (
    <SectionCard title="Weekly availability">
      <div className="space-y-3">
        {WEEKDAY_LABELS.map((label, day) => {
          const windows = byDay.get(day) ?? [];
          return (
            <div key={day} className="flex flex-wrap items-start justify-between gap-2 border-b border-line-soft pb-3 last:border-0 last:pb-0">
              <span className="w-24 shrink-0 pt-1 text-sm font-medium text-ink">{label}</span>
              <div className="flex flex-1 flex-wrap items-center gap-2">
                {windows.length === 0 && addingDay !== day && (
                  <span className="text-sm text-ink-faint">No windows set</span>
                )}
                {windows.map((w) => (
                  <div
                    key={w.id}
                    className={`flex items-center gap-2 rounded-md border px-2.5 py-1 text-sm ${
                      w.active ? 'border-line bg-white' : 'border-line-soft bg-slate-50 text-ink-faint line-through'
                    }`}
                  >
                    <span>
                      {formatTime(w.start_time)} – {formatTime(w.end_time)}
                    </span>
                    <button
                      className="focus-ring text-ink-faint hover:text-ink"
                      onClick={() => w.id && toggleMutation.mutate({ id: w.id, active: !w.active })}
                      title={w.active ? 'Deactivate' : 'Activate'}
                    >
                      {w.active ? 'Active' : 'Inactive'}
                    </button>
                    <button
                      className="focus-ring text-ink-faint hover:text-danger-600"
                      onClick={() => w.id && deleteMutation.mutate(w.id)}
                      aria-label="Delete window"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}

                {addingDay === day ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="time"
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                      className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
                    />
                    <span className="text-ink-faint">–</span>
                    <input
                      type="time"
                      value={end}
                      onChange={(e) => setEnd(e.target.value)}
                      className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
                    />
                    <Button size="sm" variant="primary" loading={createMutation.isPending} onClick={() => createMutation.mutate()}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setAddingDay(null)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="ghost" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setAddingDay(day)}>
                    Add window
                  </Button>
                )}
              </div>
            </div>
          );
        })}
        {(query.data ?? []).length === 0 && addingDay === null && (
          <EmptyState title="No recurring availability configured" description="Add working windows for each day recruiters are open to interviews." />
        )}
      </div>
    </SectionCard>
  );
}
