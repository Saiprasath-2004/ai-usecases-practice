import type { DerivedNotificationKind } from '../types';

const STORAGE_KEY = 'ats_frontend_notification_prefs_v1';

export type NotificationPrefs = Record<DerivedNotificationKind, boolean>;

export const DEFAULT_NOTIFICATION_PREFS: NotificationPrefs = {
  evaluation_failed: true,
  needs_review: true,
  on_hold: true,
  follow_up_sent: true,
  interview_scheduled: true,
};

/**
 * There's no notification-preferences endpoint on the backend (there's no
 * notification backend at all — see api/notifications.ts). These toggles
 * are stored in this browser's localStorage only; they don't sync across
 * devices and there's nothing to fetch on first load elsewhere.
 */
export function getNotificationPrefs(): NotificationPrefs {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_NOTIFICATION_PREFS, ...JSON.parse(raw) } : DEFAULT_NOTIFICATION_PREFS;
  } catch {
    return DEFAULT_NOTIFICATION_PREFS;
  }
}

export function setNotificationPrefs(prefs: NotificationPrefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Storage unavailable — preferences just won't persist this session.
  }
}
