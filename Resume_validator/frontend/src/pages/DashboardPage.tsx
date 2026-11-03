import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Briefcase,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  PauseCircle,
  Users,
  XCircle,
} from 'lucide-react';
import { useAllApplications } from '../hooks/useAllApplications';
import { buildRecentJobs, summarizeDashboard } from '../api/dashboard';
import { listCachedInterviews } from '../api/interviews';
import { deriveNotifications } from '../api/notifications';
import { formatDateTime } from '../lib/format';
import {
  Card,
  EmptyState,
  LoadingState,
  PageError,
  PageHeader,
  ScorePill,
  SectionCard,
  StageBadge,
} from '../components/Primitives';
import { PartialDataNotice } from '../components/PartialDataNotice';

function StatCard({
  label,
  value,
  icon,
  onClick,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <Card
      className={`flex items-center gap-3 p-4 ${onClick ? 'cursor-pointer transition-shadow hover:shadow-raised' : ''}`}
      onClick={onClick}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-50 text-brand-600">{icon}</div>
      <div>
        <p className="text-xl font-semibold text-ink">{value}</p>
        <p className="text-xs text-ink-soft">{label}</p>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { jobs, flat, isLoading, isError, partial } = useAllApplications();

  if (isLoading) return <LoadingState label="Loading dashboard…" />;
  if (isError) return <PageError message="Couldn't load one or more jobs' candidates." />;

  const summary = summarizeDashboard(jobs, flat);
  const recentJobs = buildRecentJobs(jobs, flat);
  const pendingReview = flat.filter((a) => a.pipeline_stage === 'Needs Review' && a.evaluation_status === 'Completed').slice(0, 6);
  const notifications = deriveNotifications(flat).slice(0, 5);
  const upcomingInterviews = listCachedInterviews()
    .filter((i) => new Date(i.scheduledAt).getTime() > Date.now())
    .slice(0, 5);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Your hiring activity across every job." />

      <PartialDataNotice show={partial} />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total Jobs" value={summary.totalJobs} icon={<Briefcase className="h-[18px] w-[18px]" />} onClick={() => navigate('/jobs')} />
        <StatCard label="Total Candidates" value={summary.totalCandidates} icon={<Users className="h-[18px] w-[18px]" />} onClick={() => navigate('/candidates')} />
        <StatCard label="Evaluated" value={summary.evaluated} icon={<CheckCircle2 className="h-[18px] w-[18px]" />} />
        <StatCard label="Shortlisted" value={summary.strongMatches} icon={<CheckCircle2 className="h-[18px] w-[18px]" />} />
        <StatCard label="Needs Review" value={summary.needsReview} icon={<ClipboardCheck className="h-[18px] w-[18px]" />} onClick={() => navigate('/human-review')} />
        <StatCard label="On Hold" value={summary.onHold} icon={<PauseCircle className="h-[18px] w-[18px]" />} />
        <StatCard label="Rejected" value={summary.rejected} icon={<XCircle className="h-[18px] w-[18px]" />} />
        <StatCard label="Upcoming Interviews" value={summary.upcomingInterviews} icon={<CalendarClock className="h-[18px] w-[18px]" />} onClick={() => navigate('/interviews')} />
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <SectionCard title="Recent jobs" action={<button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => navigate('/jobs')}>View all</button>}>
          {recentJobs.length === 0 ? (
            <EmptyState title="No jobs yet" />
          ) : (
            <div className="divide-y divide-line-soft">
              {recentJobs.map(({ job, candidateCount, evaluatedCount }) => (
                <button
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="focus-ring flex w-full items-center justify-between py-2.5 text-left"
                >
                  <div>
                    <p className="text-sm font-medium text-ink">{job.title}</p>
                    <p className="text-xs text-ink-faint">
                      {job.department} · {job.location}
                    </p>
                  </div>
                  <p className="text-xs text-ink-soft">
                    {evaluatedCount}/{candidateCount} evaluated
                  </p>
                </button>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Hiring pipeline">
          <div className="space-y-2.5">
            {(
              [
                ['Shortlisted', summary.strongMatches],
                ['Needs Review', summary.needsReview],
                ['On Hold', summary.onHold],
                ['Rejected', summary.rejected],
              ] as const
            ).map(([stage, count]) => (
              <div key={stage} className="flex items-center gap-3">
                <div className="w-32 shrink-0">
                  <StageBadge stage={stage} />
                </div>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${summary.totalCandidates ? (count / summary.totalCandidates) * 100 : 0}%` }}
                  />
                </div>
                <span className="w-6 text-right text-sm text-ink-soft">{count}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Pending recruiter actions" action={<button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => navigate('/human-review')}>Open Recruiter Review</button>}>
          {pendingReview.length === 0 ? (
            <EmptyState title="Nothing pending" />
          ) : (
            <div className="divide-y divide-line-soft">
              {pendingReview.map((a) => (
                <button
                  key={a.application_id}
                  onClick={() => navigate(`/applications/${a.application_id}`)}
                  className="focus-ring flex w-full items-center justify-between py-2.5 text-left"
                >
                  <div>
                    <p className="text-sm font-medium text-ink">{a.candidate_name}</p>
                    <p className="text-xs text-ink-faint">{a.jobTitle}</p>
                  </div>
                  <ScorePill score={a.overall_score} />
                </button>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Upcoming interviews" action={<button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => navigate('/interviews')}>View all</button>}>
          {upcomingInterviews.length === 0 ? (
            <EmptyState
              title="Nothing scheduled"
              description="Interviews you schedule will show here."
            />
          ) : (
            <div className="divide-y divide-line-soft">
              {upcomingInterviews.map((i) => (
                <div key={i.applicationId} className="flex items-center justify-between py-2.5">
                  <div>
                    <p className="text-sm font-medium text-ink">{i.candidateEmail}</p>
                    <p className="text-xs text-ink-faint">{formatDateTime(i.scheduledAt)}</p>
                  </div>
                  <span className="text-xs text-ink-soft">{i.status.replace(/([a-z])([A-Z])/g, '$1 $2')}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      {notifications.length > 0 && (
        <SectionCard title="Recent activity" className="mt-5">
          <div className="space-y-2">
            {notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => navigate(`/applications/${n.applicationId}`)}
                className="focus-ring flex w-full items-start gap-2 rounded-md py-1.5 text-left text-sm hover:bg-slate-50"
              >
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint" />
                <span className="text-ink-soft">
                  <span className="font-medium text-ink">{n.title}: </span>
                  {n.detail}
                </span>
              </button>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}
