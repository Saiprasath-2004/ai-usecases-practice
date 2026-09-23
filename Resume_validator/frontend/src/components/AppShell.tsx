import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Briefcase, Sparkles } from 'lucide-react';

export default function AppShell() {
  return (
    <div className="min-h-screen">
      <div className="mx-auto flex max-w-[1400px]">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line px-5 py-6 md:flex">
          <div className="mb-8 flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ink text-paper font-display text-sm">
              A
            </div>
            <div>
              <p className="font-display text-[15px] leading-tight text-ink">Recruiter Console</p>
              <p className="text-[11px] text-ink-faint">ATS Agent</p>
            </div>
          </div>

          <nav className="flex flex-col gap-1">
            <NavItem to="/" icon={<Briefcase className="h-4 w-4" />} label="Jobs" end />
            <NavItem to="/quick-evaluate" icon={<Sparkles className="h-4 w-4" />} label="Quick evaluate" />
          </nav>

          <div className="mt-auto rounded-card border border-line bg-panel px-3.5 py-3 text-[11px] leading-relaxed text-ink-faint">
            Connects to the FastAPI backend at
            <code className="mx-1 rounded bg-paper px-1 py-0.5 font-mono text-[10px]">/jobs</code>
            and
            <code className="mx-1 rounded bg-paper px-1 py-0.5 font-mono text-[10px]">/applications</code>.
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-6 py-8 md:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavItem({
  to,
  icon,
  label,
  end,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `focus-ring flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
          isActive ? 'bg-ink text-paper' : 'text-ink-soft hover:bg-panel'
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
