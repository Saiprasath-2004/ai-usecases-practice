import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Building2, MapPin, Plus } from 'lucide-react';
import { createJobFromInput, listJobs } from '../api/jobs';
import { EmptyState, PageError, Spinner } from '../components/Primitives';
import { useToast } from '../components/Toast';

export default function JobsListPage() {
  const qc = useQueryClient();
  const { push } = useToast();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
  });

  const createJob = useMutation({
    mutationFn: () => createJobFromInput({
      title: 'AI Platform Engineer',
      department: 'Engineering',
      location: 'Remote',
      employment_type: 'Full-time',
      job_description_text: 'Sample job description from data/jd.txt',
      job_description_source: 'data/jd.txt',
      required_skills: '[]',
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      push('success', 'Job opening created from the repository data.');
    },
    onError: (err) => push('error', (err as Error)?.message || 'Could not create the job opening.'),
  });

  return (
    <div>
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-wide text-ink-faint">Requisitions</p>
          <h1 className="mt-1 font-display text-3xl text-ink">Open jobs</h1>
          <p className="mt-2 max-w-xl text-sm text-ink-faint">
            Pick a job to see its applicant pipeline, run bulk evaluation, and act on candidates.
          </p>
        </div>

        <button
          onClick={() => createJob.mutate()}
          disabled={createJob.isPending}
          className="focus-ring inline-flex items-center gap-2 self-start rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-paper hover:opacity-90 disabled:opacity-50"
        >
          {createJob.isPending ? <Spinner className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          Create job from input data
        </button>
      </header>

      {isLoading && (
        <div className="flex items-center gap-2 py-16 justify-center text-ink-faint">
          <Spinner className="h-5 w-5" /> Loading jobs…
        </div>
      )}

      {isError && (
        <PageError
          message={(error as Error)?.message || 'Could not reach the API.'}
          onRetry={() => refetch()}
        />
      )}

      {data && data.length === 0 && (
        <EmptyState
          title="No job requisitions yet"
          description="The app can create one automatically from the sample job description in data/jd.txt."
          action={
            <button onClick={() => createJob.mutate()} className="rounded-md bg-ink px-3 py-2 text-sm font-medium text-paper">
              Load sample job
            </button>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="focus-ring group flex flex-col rounded-card border border-line bg-panel p-5 shadow-card transition-transform hover:-translate-y-0.5 hover:shadow-lift"
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="font-display text-lg leading-snug text-ink">{job.title}</h2>
                <ArrowUpRight className="h-4 w-4 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </div>

              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-faint">
                <span className="flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5" /> {job.department}
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" /> {job.location}
                </span>
              </div>

              <p className="mt-3 line-clamp-3 text-sm text-ink-soft/80">{job.job_description_text}</p>

              <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                <span className="rounded-full bg-paper px-2.5 py-1 text-[11px] font-medium text-ink-soft">
                  {job.employment_type}
                </span>
                <span className="text-[11px] font-medium text-moss-600">{job.evaluation_status}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
