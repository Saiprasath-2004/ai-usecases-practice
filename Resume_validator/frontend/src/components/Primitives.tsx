import React from 'react';
import { Loader2 } from 'lucide-react';
import { formatScore, scoreTone } from '../lib/format';
import type { PipelineStage } from '../types';

const TONE_RING: Record<string, string> = {
  high: '#3E7A4F',
  mid: '#C0812F',
  low: '#B4432F',
  none: '#C9C4B6',
};

export function ScoreRing({ score, size = 44 }: { score: number | null | undefined; size?: number }) {
  const tone = scoreTone(score);
  const pct = Math.max(0, Math.min(100, score ?? 0));
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = TONE_RING[tone];

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#EAE6DA" strokeWidth={4} fill="none" />
        {score != null && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={4}
            fill="none"
            strokeDasharray={c}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono text-[11px] font-medium text-ink-soft">{formatScore(score)}</span>
      </div>
    </div>
  );
}

const STAGE_STYLES: Record<PipelineStage, { bg: string; text: string; dot: string }> = {
  Shortlisted: { bg: 'bg-moss-50', text: 'text-moss-600', dot: 'bg-moss-500' },
  'Needs Review': { bg: 'bg-amber-50', text: 'text-amber-600', dot: 'bg-amber-500' },
  'On Hold': { bg: 'bg-violet-50', text: 'text-violet-600', dot: 'bg-violet-500' },
  Rejected: { bg: 'bg-rust-50', text: 'text-rust-600', dot: 'bg-rust-500' },
};

export function StageBadge({ stage }: { stage: PipelineStage }) {
  const style = STAGE_STYLES[stage];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${style.bg} ${style.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {stage}
    </span>
  );
}

export function Spinner({ className = '' }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} />;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-line bg-panel/60 px-8 py-16 text-center">
      <h3 className="font-display text-lg text-ink">{title}</h3>
      {description && <p className="mt-2 max-w-sm text-sm text-ink-faint">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function PageError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-card border border-rust-200 bg-rust-50 px-5 py-4 text-sm text-rust-600">
      <p className="font-medium">Something went wrong</p>
      <p className="mt-1 text-rust-600/90">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 rounded-md border border-rust-200 bg-white px-3 py-1.5 text-xs font-medium text-rust-600 hover:bg-rust-50 focus-ring">
          Try again
        </button>
      )}
    </div>
  );
}
