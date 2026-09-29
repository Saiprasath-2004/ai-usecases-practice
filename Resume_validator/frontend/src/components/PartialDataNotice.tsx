import { useQueryClient } from '@tanstack/react-query';
import { Button, Notice } from './Primitives';

/** Shown when some jobs' candidates couldn't be loaded, so totals never look complete when they aren't. */
export function PartialDataNotice({ show }: { show: boolean }) {
  const queryClient = useQueryClient();
  if (!show) return null;
  return (
    <div className="mb-5">
      <Notice tone="warning">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>Some jobs' candidates couldn't be loaded, so these numbers may be incomplete.</span>
          <Button size="sm" variant="secondary" onClick={() => queryClient.invalidateQueries({ queryKey: ['job-applications'] })}>
            Try again
          </Button>
        </div>
      </Notice>
    </div>
  );
}
