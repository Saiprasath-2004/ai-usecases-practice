import { Check } from 'lucide-react';
import type { EvaluationStatus } from '../../types';

/**
 * Makes the sequence obvious at a glance:
 * AI evaluates -> evidence is shown -> recruiter reviews -> recruiter decides.
 * The last two steps always belong to the recruiter.
 */
export function ReviewFlow({ evaluationStatus }: { evaluationStatus: EvaluationStatus }) {
  const evaluated = evaluationStatus === 'Completed';
  const steps = [
    { label: 'AI evaluated', done: evaluated, owner: 'AI' },
    { label: 'Evidence shown', done: evaluated, owner: 'AI' },
    { label: 'You review', done: false, owner: 'Recruiter' },
    { label: 'You decide', done: false, owner: 'Recruiter' },
  ];

  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" aria-label="Review process">
      {steps.map((step, index) => (
        <li key={step.label} className="inline-flex items-center gap-2">
          {index > 0 && <span className="h-px w-5 bg-line" aria-hidden />}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium ${
              step.owner === 'Recruiter'
                ? 'border-brand-200 bg-brand-50 text-brand-700'
                : step.done
                  ? 'border-success-200 bg-success-50 text-green-700'
                  : 'border-line bg-white text-ink-soft'
            }`}
          >
            {step.done && <Check className="h-3 w-3" />}
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
}
