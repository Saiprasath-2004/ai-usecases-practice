import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CalendarCheck, ClipboardList, PauseCircle, Send } from 'lucide-react';
import { useAllApplications } from '../hooks/useAllApplications';
import { deriveNotifications } from '../api/notifications';
import { getNotificationPrefs } from '../lib/notificationPrefs';
import type { DerivedNotificationKind } from '../types';
import { EmptyState, LoadingState, PageError, PageHeader, SectionCard } from '../components/Primitives';

const ICONS: Record<DerivedNotificationKind, React.ReactNode> = {
  evaluation_failed: <AlertTriangle className="h-4 w-4 text-danger-600" />,
  needs_review: <ClipboardList className="h-4 w-4 text-warning-600" />,
  on_hold: <PauseCircle className="h-4 w-4 text-hold-600" />,
  follow_up_sent: <Send className="h-4 w-4 text-brand-600" />,
  interview_scheduled: <CalendarCheck className="h-4 w-4 text-success-600" />,
};

export function NotificationsPage() {
  const navigate = useNavigate();
  const { flat, isLoading, isError } = useAllApplications();

  if (isLoading) return <LoadingState label="Loading notifications…" />;
  if (isError) return <PageError message="Couldn't load one or more jobs' candidates." />;

  const prefs = getNotificationPrefs();
  const notifications = deriveNotifications(flat).filter((n) => prefs[n.kind]);

  return (
    <div>
      <PageHeader title="Notifications" subtitle="What needs your attention right now." />


      <SectionCard>
        {notifications.length === 0 ? (
          <EmptyState title="You're all caught up" description="Nothing needs your attention right now." />
        ) : (
          <div className="divide-y divide-line">
            {notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => navigate(`/applications/${n.applicationId}`)}
                className="focus-ring flex w-full items-start gap-3 py-3 text-left hover:bg-slate-50/70"
              >
                <div className="mt-0.5">{ICONS[n.kind]}</div>
                <div>
                  <p className="text-sm font-medium text-ink">{n.title}</p>
                  <p className="text-sm text-ink-soft">{n.detail}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
