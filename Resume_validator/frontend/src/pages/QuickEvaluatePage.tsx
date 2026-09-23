import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send, Sparkles } from 'lucide-react';
import api from '../api/client';
import { fetchEvaluationStatus, startEvaluation, submitFollowupReply, submitReview } from '../api/candidates';
import { PageError, Spinner } from '../components/Primitives';
import { useToast } from '../components/Toast';

interface CandidateOption {
  name: string;
  label: string;
  path: string;
}

export default function QuickEvaluatePage() {
  const [jdPath, setJdPath] = useState('data/jd.txt');
  const [resumePath, setResumePath] = useState('input/resume_1.pdf');
  const [activeId, setActiveId] = useState<string | null>(null);
  const { push } = useToast();

  const { data: candidateOptions, isLoading: resumesLoading } = useQuery({
    queryKey: ['candidate-files'],
    queryFn: async () => {
      const { data } = await api.get('/candidates/available');
      return data.resumes as CandidateOption[];
    },
  });

  const start = useMutation({
    mutationFn: () => startEvaluation(jdPath, resumePath),
    onSuccess: (res) => {
      setActiveId(res.id);
      push('success', 'Evaluation started.');
    },
    onError: (err) => push('error', (err as Error).message || 'Could not start evaluation.'),
  });

  const statusQuery = useQuery({
    queryKey: ['quick-eval', activeId],
    queryFn: () => fetchEvaluationStatus(activeId as string),
    enabled: !!activeId,
    refetchInterval: (q) => (q.state.data && ['completed', 'failed'].includes(q.state.data.status) ? false : 2500),
  });

  useEffect(() => {
    if (candidateOptions && candidateOptions.length > 0 && !resumePath) {
      setResumePath(candidateOptions[0].path);
    }
  }, [candidateOptions, resumePath]);

  const summary = useMemo(() => {
    if (!activeId) return null;
    if (statusQuery.data?.status === 'completed') {
      if (statusQuery.data.verdict === 'SELECT') return 'Strong match';
      if (statusQuery.data.verdict === 'REJECT') return 'Rejected';
      return 'Needs review';
    }
    return null;
  }, [activeId, statusQuery.data?.status, statusQuery.data?.verdict]);

  return (
    <div className="max-w-3xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-wide text-ink-faint">Single resume flow</p>
        <h1 className="mt-1 font-display text-3xl text-ink">Quick evaluate</h1>
        <p className="mt-2 text-sm text-ink-faint">
          Use the sample JD and candidate resumes from the project data to run a single evaluation and review the final score bucket.
        </p>
      </header>

      <div className="rounded-card border border-line bg-panel p-5 shadow-card">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Job description path" value={jdPath} onChange={setJdPath} />
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-ink-faint">Candidate resume</span>
            <select
              value={resumePath}
              onChange={(e) => setResumePath(e.target.value)}
              className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
              disabled={resumesLoading || !candidateOptions}
            >
              {candidateOptions?.map((candidate) => (
                <option key={candidate.path} value={candidate.path}>
                  {candidate.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          onClick={() => start.mutate()}
          disabled={start.isPending}
          className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2.5 text-sm font-medium text-paper hover:opacity-90 disabled:opacity-50"
        >
          {start.isPending ? <Spinner className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          Single evaluate
        </button>
      </div>

      {statusQuery.data && (
        <div className="mt-6 rounded-card border border-line bg-panel p-5 shadow-card">
          <div className="flex items-center justify-between">
            <p className="font-mono text-xs text-ink-faint">Run {activeId}</p>
            <StatusPill status={statusQuery.data.status} />
          </div>

          {statusQuery.data?.error && <p className="mt-3 text-sm text-rust-600">{statusQuery.data.error}</p>}

          {statusQuery.data?.verdict && (
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <ResultCard title="Strong match" active={statusQuery.data.verdict === 'SELECT'} tint="moss" />
              <ResultCard title="Needs review" active={statusQuery.data.verdict === 'ESCALATE'} tint="amber" />
              <ResultCard title="Rejected" active={statusQuery.data.verdict === 'REJECT'} tint="rust" />
            </div>
          )}

          {summary && <p className="mt-4 text-sm font-medium text-ink">Current bucket: {summary}</p>}

          {statusQuery.data?.narrative && (
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{statusQuery.data.narrative}</p>
          )}

          {statusQuery.data?.status === 'awaiting_followup' && statusQuery.data.followup_questions && (
            <FollowupForm id={activeId as string} questions={statusQuery.data.followup_questions} />
          )}

          {statusQuery.data?.status === 'awaiting_review' && <ReviewForm id={activeId as string} />}
        </div>
      )}

      {statusQuery.isLoading && (
        <div className="mt-6 rounded-card border border-line bg-panel p-5 text-sm text-ink-faint shadow-card">
          <Spinner className="mr-2 inline h-4 w-4" /> Checking evaluation status…
        </div>
      )}

      {statusQuery.isError && (
        <div className="mt-6">
          <PageError message={(statusQuery.error as Error)?.message || 'Could not fetch status.'} />
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-ink-faint">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
      />
    </label>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    running: 'bg-amber-50 text-amber-600',
    awaiting_followup: 'bg-violet-50 text-violet-600',
    awaiting_review: 'bg-violet-50 text-violet-600',
    completed: 'bg-moss-50 text-moss-600',
    failed: 'bg-rust-50 text-rust-600',
  };
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${map[status] || 'bg-paper text-ink-faint'}`}>{status}</span>;
}

function ResultCard({ title, active, tint }: { title: string; active: boolean; tint: 'moss' | 'amber' | 'rust' }) {
  const colors = {
    moss: active ? 'border-moss-300 bg-moss-50 text-moss-700' : 'border-line bg-white text-ink-faint',
    amber: active ? 'border-amber-300 bg-amber-50 text-amber-700' : 'border-line bg-white text-ink-faint',
    rust: active ? 'border-rust-300 bg-rust-50 text-rust-700' : 'border-line bg-white text-ink-faint',
  };

  return (
    <div className={`rounded-md border px-3 py-3 text-sm font-medium ${colors[tint]}`}>
      {title}
    </div>
  );
}

function FollowupForm({ id, questions }: { id: string; questions: string[] }) {
  const [reply, setReply] = useState('');
  const { push } = useToast();
  const submit = useMutation({
    mutationFn: () => submitFollowupReply(id, reply),
    onSuccess: (res) => push('success', res.message),
    onError: (err) => push('error', (err as Error).message || 'Could not submit reply.'),
  });

  return (
    <div className="mt-4 border-t border-line pt-4">
      <p className="mb-2 text-sm font-medium text-ink">Follow-up questions</p>
      <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-ink-soft">
        {questions.map((q, i) => (
          <li key={i}>{q}</li>
        ))}
      </ul>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        rows={3}
        placeholder="Candidate's reply…"
        className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
      />
      <button
        onClick={() => submit.mutate()}
        disabled={submit.isPending || !reply.trim()}
        className="focus-ring mt-2 inline-flex items-center gap-1.5 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink-soft hover:bg-paper disabled:opacity-50"
      >
        <Send className="h-3.5 w-3.5" /> Submit reply
      </button>
    </div>
  );
}

function ReviewForm({ id }: { id: string }) {
  const [comments, setComments] = useState('');
  const { push } = useToast();
  const submit = useMutation({
    mutationFn: (decision: 'Approve' | 'Reject' | 'Request More Info') => submitReview(id, decision, comments),
    onSuccess: (res) => push('success', res.message),
    onError: (err) => push('error', (err as Error).message || 'Could not submit review.'),
  });

  return (
    <div className="mt-4 border-t border-line pt-4">
      <p className="mb-2 text-sm font-medium text-ink">Human review</p>
      <textarea
        value={comments}
        onChange={(e) => setComments(e.target.value)}
        rows={2}
        placeholder="Comments (optional)…"
        className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
      />
      <div className="mt-2 flex gap-2">
        <button onClick={() => submit.mutate('Approve')} className="focus-ring rounded-md border border-moss-200 bg-white px-3 py-2 text-xs font-medium text-moss-600 hover:bg-moss-50">
          Approve
        </button>
        <button onClick={() => submit.mutate('Request More Info')} className="focus-ring rounded-md border border-amber-200 bg-white px-3 py-2 text-xs font-medium text-amber-600 hover:bg-amber-50">
          Request more info
        </button>
        <button onClick={() => submit.mutate('Reject')} className="focus-ring rounded-md border border-rust-200 bg-white px-3 py-2 text-xs font-medium text-rust-600 hover:bg-rust-50">
          Reject
        </button>
      </div>
    </div>
  );
}
