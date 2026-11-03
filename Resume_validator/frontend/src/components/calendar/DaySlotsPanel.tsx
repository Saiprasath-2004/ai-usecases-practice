import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAvailableSlots, listBlocks } from '../../api/calendar';
import { listCachedInterviews } from '../../api/interviews';
import { RECRUITER_ID } from '../../types';
import { formatTime } from '../../lib/format';
import { Badge, LoadingState, PageError, SectionCard } from '../Primitives';
import { describeError } from '../../lib/errors';

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function DaySlotsPanel() {
  const [date, setDate] = useState(todayIso());
  const [duration, setDuration] = useState(60);

  const slotsQuery = useQuery({
    queryKey: ['calendar-slots', RECRUITER_ID, date, duration],
    queryFn: () => getAvailableSlots(RECRUITER_ID, date, duration),
  });

  const blocksQuery = useQuery({
    queryKey: ['calendar-blocks', RECRUITER_ID],
    queryFn: () => listBlocks(RECRUITER_ID),
  });

  const blocksForDay = (blocksQuery.data ?? []).filter((b) => b.start_at.slice(0, 10) === date);
  const interviewsForDay = listCachedInterviews().filter((i) => i.scheduledAt.slice(0, 10) === date);

  return (
    <SectionCard
      title="Day view"
      action={
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
          />
          <select
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="focus-ring h-8 rounded-md border border-line px-2 text-sm"
          >
            {[15, 30, 45, 60, 90, 120].map((d) => (
              <option key={d} value={d}>
                {d} min
              </option>
            ))}
          </select>
        </div>
      }
    >
      <div className="mb-4">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-faint">Available</p>
        {slotsQuery.isLoading ? (
          <LoadingState label="Checking availability…" />
        ) : slotsQuery.isError ? (
          <PageError message={describeError(slotsQuery.error).message} />
        ) : slotsQuery.data && slotsQuery.data.slots.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {slotsQuery.data.slots.map((s) => (
              <Badge key={s.start} tone="success">
                {formatTime(s.start)} – {formatTime(s.end)}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-ink-faint">No open slots this day at this duration.</p>
        )}
      </div>

      <div className="mb-4">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-faint">Blocked</p>
        {blocksForDay.length === 0 ? (
          <p className="text-sm text-ink-faint">No blocked periods this day.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {blocksForDay.map((b) => (
              <Badge key={b.id} tone="neutral">
                {b.all_day ? 'All day' : `${formatTime(b.start_at)} – ${formatTime(b.end_at)}`}
                {b.reason ? ` · ${b.reason}` : ''}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-ink-faint">
          Interviews
        </p>
        {interviewsForDay.length === 0 ? (
          <p className="text-sm text-ink-faint">No interviews recorded for this day.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {interviewsForDay.map((i) => (
              <Badge key={i.applicationId} tone="brand">
                {formatTime(i.scheduledAt)} · {i.candidateEmail}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
