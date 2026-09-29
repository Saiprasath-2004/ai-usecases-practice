import { useState } from 'react';
import { AvailabilityEditor } from '../components/calendar/AvailabilityEditor';
import { useToast } from '../components/Toast';
import { DEFAULT_NOTIFICATION_PREFS, getNotificationPrefs, setNotificationPrefs } from '../lib/notificationPrefs';
import { Button, PageHeader, SectionCard } from '../components/Primitives';

const LABELS: Record<keyof typeof DEFAULT_NOTIFICATION_PREFS, string> = {
  evaluation_failed: 'Evaluation failed',
  needs_review: 'Candidate waiting for review',
  on_hold: 'Candidate on hold',
  follow_up_sent: 'Follow-up in progress',
  interview_scheduled: 'Interview response recorded',
};

export function SettingsPage() {
  const toast = useToast();
  const [prefs, setPrefs] = useState(getNotificationPrefs());

  return (
    <div>
      <PageHeader title="Settings" subtitle="Your profile, availability and notification preferences." />

      <div className="space-y-5">
        <SectionCard title="Recruiter profile">
          <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wide text-ink-faint">Name</dt>
              <dd className="text-ink">Recruiter</dd>
            </div>
          </dl>
        </SectionCard>

        <AvailabilityEditor />

        <SectionCard
          title="Notification preferences"
          action={
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                setNotificationPrefs(prefs);
                toast.push('success', 'Preferences saved.');
              }}
            >
              Save
            </Button>
          }
        >
          <p className="mb-3 text-sm text-ink-soft">
            Choose which updates appear on your Notifications page.
          </p>
          <div className="space-y-2">
            {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
              <label key={key} className="flex items-center gap-2.5 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={prefs[key]}
                  onChange={(e) => setPrefs({ ...prefs, [key]: e.target.checked })}
                  className="h-4 w-4 rounded border-line text-brand-600 focus-ring"
                />
                {LABELS[key]}
              </label>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
