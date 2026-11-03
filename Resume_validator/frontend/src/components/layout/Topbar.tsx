import { Bell, Search } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAllApplications } from '../../hooks/useAllApplications';
import { deriveNotifications } from '../../api/notifications';
import { Avatar } from '../Primitives';

export function Topbar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const { flat } = useAllApplications();
  const notificationCount = deriveNotifications(flat).length;

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    navigate(trimmed ? `/candidates?q=${encodeURIComponent(trimmed)}` : '/candidates');
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-line bg-surface px-6">
      <form onSubmit={handleSearch} className="relative w-full max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search candidates or jobs…"
          className="focus-ring h-9 w-full rounded-md border border-line bg-bg pl-9 pr-3 text-sm placeholder:text-ink-faint"
        />
      </form>

      <div className="ml-auto flex items-center gap-4">
        <button
          onClick={() => navigate('/notifications')}
          className="focus-ring relative rounded-md p-2 text-ink-soft hover:bg-slate-50 hover:text-ink"
          aria-label="Notifications"
        >
          <Bell className="h-[18px] w-[18px]" />
          {notificationCount > 0 && (
            <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-brand-600" />
          )}
        </button>
        <div className="flex items-center gap-2.5 border-l border-line pl-4">
          <Avatar name="Recruiter" size={30} />
          <p className="text-sm font-medium text-ink">Recruiter</p>
        </div>
      </div>
    </header>
  );
}
