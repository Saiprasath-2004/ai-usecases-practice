import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, Plus, Users } from 'lucide-react';
import { createJob, listJobs } from '../api/jobs';
import { useJobApplications } from '../hooks/useJobApplications';
import type { JobCreate, JobRead } from '../types';
import { Button, Card, EmptyState, LoadingState, PageError, PageHeader } from '../components/Primitives';
import { useToast } from '../components/Toast';
import { describeError } from '../lib/errors';

const EMPTY_FORM: JobCreate = {
  title: '',
  department: '',
  location: '',
  employment_type: 'Full-time',
  job_description_text: '',
  job_description_source: '',
  required_skills: '',
};

function JobCard({ job }: { job: JobRead }) {
  const navigate = useNavigate();
  const { applications, isLoading, isError } = useJobApplications(job.id);
  const candidateCount = applications.length;

  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-ink">{job.title}</h3>
          <p className="mt-0.5 text-sm text-ink-soft">{job.department}</p>
        </div>
        <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
          {job.evaluation_status}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-faint">
        <span className="inline-flex items-center gap-1">
          <MapPin className="h-3.5 w-3.5" /> {job.location}
        </span>
        <span className="inline-flex items-center gap-1">
          <Briefcase className="h-3.5 w-3.5" /> {job.employment_type}
        </span>
        <span className="inline-flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />{' '}
          {isLoading ? 'Loading…' : isError ? "Couldn't load candidates" : `${candidateCount} candidate${candidateCount === 1 ? '' : 's'}`}
        </span>
      </div>
      <div className="mt-4 flex gap-2">
        <Button size="sm" variant="primary" onClick={() => navigate(`/jobs/${job.id}`)}>
          View job
        </Button>
        <Button size="sm" variant="secondary" onClick={() => navigate(`/jobs/${job.id}/candidates`)}>
          Candidates
        </Button>
      </div>
    </Card>
  );
}

export function JobsListPage() {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<JobCreate>(EMPTY_FORM);
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const jobsQuery = useQuery({ queryKey: ['jobs'], queryFn: listJobs });

  const createMutation = useMutation({
    mutationFn: () => createJob({ ...form, job_description_source: form.job_description_source || `manual:${form.title}` }),
    onSuccess: (job) => {
      toast.push('success', `${job.title} created.`);
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setShowForm(false);
      setForm(EMPTY_FORM);
      navigate(`/jobs/${job.id}`);
    },
    onError: (err) => toast.push('error', describeError(err).message),
  });

  if (jobsQuery.isLoading) return <LoadingState label="Loading jobs…" />;
  if (jobsQuery.isError) return <PageError message={describeError(jobsQuery.error).message} />;

  const jobs = jobsQuery.data ?? [];

  return (
    <div>
      <PageHeader
        title="Jobs"
        subtitle="Open requisitions and the candidates evaluated against each."
        actions={
          <Button variant="primary" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setShowForm((s) => !s)}>
            New job
          </Button>
        }
      />

      {showForm && (
        <Card className="mb-6 p-5">
          <h3 className="mb-3 text-sm font-semibold text-ink">Create a job requisition</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Title">
              <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Department">
              <input className="input" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
            </Field>
            <Field label="Location">
              <input className="input" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
            </Field>
            <Field label="Employment type">
              <select
                className="input"
                value={form.employment_type}
                onChange={(e) => setForm({ ...form, employment_type: e.target.value })}
              >
                {['Full-time', 'Part-time', 'Contract', 'Internship'].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </Field>
            <Field label="Required skills (comma-separated)" full>
              <input
                className="input"
                value={form.required_skills}
                onChange={(e) => setForm({ ...form, required_skills: e.target.value })}
                placeholder="React, Node.js, SQL"
              />
            </Field>
            <Field label="Job description" full>
              <textarea
                className="input"
                rows={4}
                value={form.job_description_text}
                onChange={(e) => setForm({ ...form, job_description_text: e.target.value })}
              />
            </Field>
          </div>
          <div className="mt-4 flex gap-2">
            <Button
              variant="primary"
              loading={createMutation.isPending}
              disabled={!form.title || !form.department || !form.job_description_text}
              onClick={() => createMutation.mutate()}
            >
              Create job
            </Button>
            <Button variant="ghost" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          description="Create your first job requisition to start collecting and evaluating candidates."
          action={
            <Button className="mt-2" variant="primary" onClick={() => setShowForm(true)}>
              New job
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, children, full }: { label: string; children: React.ReactNode; full?: boolean }) {
  return (
    <label className={`block text-xs font-medium text-ink-soft ${full ? 'sm:col-span-2' : ''}`}>
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}
