import {
  BarChart3,
  Bell,
  Briefcase,
  Calendar,
  ClipboardCheck,
  LayoutDashboard,
  Settings,
  Users,
  Video,
  Zap,
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAllApplications } from '../../hooks/useAllApplications';
import { deriveNotifications } from '../../api/notifications';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/jobs', label: 'Jobs', icon: Briefcase },
  { to: '/candidates', label: 'Candidates', icon: Users },
  { to: '/quick-evaluate', label: 'Quick Evaluate', icon: Zap },
  { to: '/human-review', label: 'Recruiter Review', icon: ClipboardCheck },
  { to: '/calendar', label: 'Calendar', icon: Calendar },
  { to: '/interviews', label: 'Interviews', icon: Video },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { flat } = useAllApplications();
  const notificationCount = deriveNotifications(flat).length;

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-line bg-surface">
      <div className="flex h-14 items-center gap-2 border-b border-line px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
          A
        </div>
        <span className="text-sm font-semibold text-ink">ATS Recruiter</span>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4 scrollbar-thin">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `focus-ring flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? 'bg-brand-50 text-brand-700' : 'text-ink-soft hover:bg-slate-50 hover:text-ink'
              }`
            }
          >
            <span className="flex items-center gap-2.5">
              <Icon className="h-4 w-4" />
              {label}
            </span>
            {label === 'Notifications' && notificationCount > 0 && (
              <span className="flex h-[18px] min-w-[1.125rem] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-semibold text-white">
                {notificationCount > 99 ? '99+' : notificationCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
