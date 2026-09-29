import React from 'react';
import { AlertTriangle, ChevronRight, Info, Inbox, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { EvaluationStatus, PipelineStage } from '../types';
import { evaluationStatusLabel, initials, scoreTone } from '../lib/format';

export type Tone = 'success' | 'warning' | 'danger' | 'hold' | 'neutral' | 'brand';

const TONE_CLASSES: Record<Tone, string> = {
  success: 'bg-success-50 text-green-700 border-success-200',
  warning: 'bg-warning-50 text-amber-700 border-warning-200',
  danger: 'bg-danger-50 text-red-700 border-danger-200',
  hold: 'bg-hold-50 text-violet-700 border-hold-200',
  neutral: 'bg-slate-100 text-ink-soft border-line',
  brand: 'bg-brand-50 text-brand-700 border-brand-200',
};

export function Badge({
  tone = 'neutral',
  children,
  icon,
  className = '',
}: {
  tone?: Tone;
  children: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium leading-none ${TONE_CLASSES[tone]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}

const STAGE_TONE: Record<PipelineStage, Tone> = {
  Shortlisted: 'success',
  'Needs Review': 'warning',
  'On Hold': 'hold',
  Rejected: 'danger',
};

export function StageBadge({ stage }: { stage: PipelineStage }) {
  return <Badge tone={STAGE_TONE[stage] ?? 'neutral'}>{stage}</Badge>;
}

const EVAL_TONE: Record<EvaluationStatus, Tone> = {
  Pending: 'neutral',
  Running: 'brand',
  Completed: 'success',
  Failed: 'danger',
};

export function EvalStatusBadge({ status }: { status: EvaluationStatus | string }) {
  const tone = EVAL_TONE[status as EvaluationStatus] ?? 'neutral';
  const spinning = status === 'Running';
  return (
    <Badge tone={tone} icon={spinning ? <Loader2 className="h-3 w-3 animate-spin" /> : undefined}>
      {evaluationStatusLabel(status)}
    </Badge>
  );
}

export function ScorePill({ score }: { score: number | null | undefined }) {
  const tone = scoreTone(score);
  const label = score == null ? '—' : Math.round(score).toString();
  return (
    <span
      className={`inline-flex h-8 min-w-[2.5rem] items-center justify-center rounded-md border px-2 font-mono text-sm font-semibold ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}

export function ScoreRing({ score, size = 56 }: { score: number | null | undefined; size?: number }) {
  const tone = scoreTone(score);
  const strokeColor =
    tone === 'success'
      ? '#16A34A'
      : tone === 'danger'
        ? '#DC2626'
        : tone === 'warning'
          ? '#D97706'
          : '#94A3B8';
  const pct = score == null ? 0 : Math.max(0, Math.min(100, score));
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E2E8F0" strokeWidth={5} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={5}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute font-mono font-semibold text-ink" style={{ fontSize: Math.max(14, size * 0.32) }}>
        {score == null ? '—' : Math.round(score)}
      </span>
    </div>
  );
}

export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initials(name)}
    </div>
  );
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return <Loader2 className={`animate-spin text-brand-600 ${className}`} />;
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-outline';
type ButtonSize = 'sm' | 'md';

const BUTTON_VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-300',
  secondary: 'bg-white text-ink border border-line hover:bg-slate-50 disabled:text-ink-faint',
  ghost: 'text-ink-soft hover:bg-slate-100 disabled:text-ink-faint',
  danger: 'bg-danger-600 text-white hover:bg-danger-700 disabled:bg-danger-300',
  'danger-outline': 'bg-white text-red-700 border border-danger-200 hover:bg-danger-50 disabled:text-ink-faint disabled:border-line disabled:hover:bg-white',
};

const BUTTON_SIZE: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
};

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon,
  className = '',
  children,
  disabled,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <button
      className={`focus-ring inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:cursor-not-allowed ${BUTTON_VARIANT[variant]} ${BUTTON_SIZE[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
      {children}
    </button>
  );
}

export function Card({
  className = '',
  children,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { className?: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-card border border-line bg-surface shadow-card ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function SectionCard({
  title,
  action,
  children,
  className = '',
}: {
  title?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          {typeof title === 'string' ? <h3 className="text-sm font-semibold text-ink">{title}</h3> : title}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </Card>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-soft">
      <Spinner className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-line bg-slate-50/60 py-14 text-center">
      <div className="mb-1 flex h-10 w-10 items-center justify-center rounded-full bg-white text-ink-faint shadow-sm">
        {icon ?? <Inbox className="h-5 w-5" />}
      </div>
      <p className="text-sm font-medium text-ink">{title}</p>
      {description && <p className="max-w-sm text-sm text-ink-soft">{description}</p>}
      {action}
    </div>
  );
}

export function PageError({ message, detail }: { message: string; detail?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-danger-200 bg-danger-50 py-14 text-center">
      <AlertTriangle className="mb-1 h-6 w-6 text-danger-600" />
      <p className="text-sm font-medium text-danger-600">{message}</p>
      {detail && <p className="max-w-md text-xs text-ink-faint">{detail}</p>}
    </div>
  );
}

export function Notice({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'warning';
  children: React.ReactNode;
}) {
  const styles =
    tone === 'warning'
      ? 'border-warning-200 bg-warning-50 text-amber-800'
      : 'border-brand-200 bg-brand-50 text-brand-700';
  const Icon = tone === 'warning' ? AlertTriangle : Info;
  return (
    <div className={`flex items-start gap-2 rounded-card border px-4 py-3 text-sm ${styles}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-line">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`focus-ring -mb-px rounded-t-md border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            active === tab.id
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-ink-soft hover:text-ink'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

/** Compact chip for skills / keywords. Matched = green, needs clarification = amber. */
export function SkillChip({
  children,
  tone = 'neutral',
}: {
  children: React.ReactNode;
  tone?: 'matched' | 'clarify' | 'neutral';
}) {
  const styles = {
    matched: 'bg-success-50 border-success-200 text-green-800',
    clarify: 'bg-warning-50 border-warning-200 text-amber-800',
    neutral: 'bg-slate-50 border-line text-ink-soft',
  }[tone];
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium leading-5 ${styles}`}>
      {children}
    </span>
  );
}

export function ProgressBar({ percent, className = '' }: { percent: number | null; className?: string }) {
  const tone = scoreTone(percent);
  const fill =
    tone === 'success' ? 'bg-success-500' : tone === 'danger' ? 'bg-danger-500' : tone === 'warning' ? 'bg-warning-500' : 'bg-slate-300';
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-slate-100 ${className}`}>
      <div className={`h-full rounded-full ${fill}`} style={{ width: `${percent ?? 0}%` }} />
    </div>
  );
}

export function Breadcrumbs({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1 text-sm text-ink-soft">
      {items.map((item, index) => (
        <span key={`${item.label}-${index}`} className="inline-flex items-center gap-1">
          {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-ink-faint" />}
          {item.to ? (
            <Link to={item.to} className="focus-ring rounded hover:text-ink hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="font-medium text-ink">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
