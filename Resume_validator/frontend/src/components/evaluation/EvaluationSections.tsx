import { AlertTriangle, Check, MessageSquarePlus } from 'lucide-react';
import type { ApplicationRead, ExperienceResult, ScoreBreakdown, WorkflowState } from '../../types';
import {
  SCORE_WEIGHTS,
  asList,
  asRecord,
  componentPercent,
  parseEvidenceGroups,
  summarizeExperience,
} from '../../lib/format';
import { Badge, Button, EmptyState, ProgressBar, SectionCard, SkillChip } from '../Primitives';

// ---------------------------------------------------------------------
// Shared data extraction — one place turns the stored record into the
// lists each section needs, so no section touches raw fields.
// ---------------------------------------------------------------------

export interface EvaluationData {
  evaluated: boolean;
  breakdown: ScoreBreakdown;
  matchedSkills: string[];
  missingSkills: string[];
  matchedResponsibilities: string[];
  missingResponsibilities: string[];
  keywordsFound: string[];
  keywordsMissing: string[];
  strengths: ReturnType<typeof parseEvidenceGroups>;
  experience: ExperienceResult;
}

export function extractEvaluation(application: ApplicationRead): EvaluationData {
  const strengths = parseEvidenceGroups(application.strengths);
  const gaps = parseEvidenceGroups(application.gaps);
  const matchedSkills = asList(application.matched_skills);
  const missingSkills = asList(application.missing_skills);
  const matchedResp = asList(application.responsibilities_matched);
  const missingResp = asList(application.responsibilities_missing);

  return {
    evaluated: application.evaluation_status === 'Completed',
    breakdown: asRecord(application.score_breakdown) as ScoreBreakdown,
    matchedSkills: matchedSkills.length ? matchedSkills : strengths.skills,
    missingSkills: missingSkills.length ? missingSkills : gaps.skills,
    matchedResponsibilities: matchedResp.length ? matchedResp : strengths.responsibilities,
    missingResponsibilities: missingResp.length ? missingResp : gaps.responsibilities,
    keywordsFound: strengths.keywords,
    keywordsMissing: gaps.keywords,
    strengths,
    experience: asRecord(application.experience_result) as ExperienceResult,
  };
}

function NotEvaluated({ text }: { text: string }) {
  return <p className="text-sm text-ink-faint">{text}</p>;
}

const VERDICT_COPY: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' }> = {
  SELECT: { label: 'Recommended for interview', tone: 'success' },
  ESCALATE: { label: 'Needs your review', tone: 'warning' },
  REJECT: { label: 'Not recommended', tone: 'danger' },
};

// ---------------------------------------------------------------------
// 4. AI Evaluation Summary
// ---------------------------------------------------------------------

export function AiSummary({
  application,
  data,
  workflowState,
}: {
  application: ApplicationRead;
  data: EvaluationData;
  workflowState?: WorkflowState | null;
}) {
  const verdict = workflowState?.verdict ? VERDICT_COPY[workflowState.verdict] : undefined;
  const skillTotal = data.matchedSkills.length + data.missingSkills.length;
  const respTotal = data.matchedResponsibilities.length + data.missingResponsibilities.length;
  const exp = summarizeExperience(data.experience);

  const facts: string[] = [];
  if (skillTotal > 0) facts.push(`${data.matchedSkills.length} of ${skillTotal} required skills matched`);
  if (respTotal > 0) facts.push(`${data.matchedResponsibilities.length} of ${respTotal} responsibilities covered`);
  if (exp) facts.push(`Experience: ${exp.label.toLowerCase()}`);

  return (
    <SectionCard
      title={
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-ink">AI Evaluation Summary</h3>
          {verdict && <Badge tone={verdict.tone}>AI recommendation: {verdict.label}</Badge>}
        </div>
      }
      action={<span className="text-xs font-medium text-brand-700">Recruiter decision required</span>}
    >
      {!data.evaluated ? (
        <NotEvaluated
          text={
            application.evaluation_status === 'Running'
              ? 'The evaluation is in progress. Results will appear here when it finishes.'
              : 'This candidate has not been evaluated yet.'
          }
        />
      ) : (
        <div className="space-y-3">
          {workflowState?.narrative && (
            <p className="text-sm leading-relaxed text-ink-soft">{workflowState.narrative}</p>
          )}
          {facts.length > 0 && (
            <ul className="space-y-1.5 text-sm text-ink">
              {facts.map((fact) => (
                <li key={fact} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint" />
                  {fact}
                </li>
              ))}
            </ul>
          )}
          {workflowState?.escalation_reason && (
            <p className="text-sm text-ink-soft">
              <span className="font-medium text-ink">Why this needs your attention: </span>
              {workflowState.escalation_reason}
            </p>
          )}
          <p className="text-xs text-ink-faint">
            The AI compared the resume with the job requirements. Review the evidence below, then make your
            decision.
          </p>
        </div>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 5. Score Breakdown
// ---------------------------------------------------------------------

export function ScoreBreakdownCard({ data }: { data: EvaluationData }) {
  const rows: { label: string; value: number | null | undefined; max: number }[] = [
    { label: 'Skills', value: data.breakdown.skill_score, max: SCORE_WEIGHTS.skills },
    { label: 'Experience', value: data.breakdown.experience_score, max: SCORE_WEIGHTS.experience },
    { label: 'Keywords', value: data.breakdown.keyword_score, max: SCORE_WEIGHTS.keywords },
    { label: 'Responsibilities', value: data.breakdown.responsibility_score, max: SCORE_WEIGHTS.responsibilities },
  ];

  return (
    <SectionCard title="Score Breakdown">
      {!data.evaluated ? (
        <NotEvaluated text="Available once the candidate has been evaluated." />
      ) : (
        <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="mb-1.5 flex items-baseline justify-between text-sm">
                <span className="text-ink-soft">{row.label}</span>
                <span className="font-mono text-xs font-semibold text-ink">
                  {row.value == null ? '—' : `${Math.round(row.value)} / ${row.max}`}
                </span>
              </div>
              <ProgressBar percent={componentPercent(row.value, row.max)} />
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 6. Skills
// ---------------------------------------------------------------------

function ChipGroup({
  label,
  items,
  tone,
}: {
  label: string;
  items: string[];
  tone: 'matched' | 'clarify' | 'neutral';
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-faint">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <SkillChip key={item} tone={tone}>
            {item}
          </SkillChip>
        ))}
      </div>
    </div>
  );
}

export function SkillsCard({ data }: { data: EvaluationData }) {
  const hasAny = data.matchedSkills.length + data.missingSkills.length + data.keywordsFound.length > 0;
  return (
    <SectionCard title="Skills">
      {!data.evaluated || !hasAny ? (
        <NotEvaluated text={data.evaluated ? 'No skills were identified for this candidate.' : 'Available once the candidate has been evaluated.'} />
      ) : (
        <div className="space-y-4">
          <ChipGroup label="Matched skills" items={data.matchedSkills} tone="matched" />
          <ChipGroup label="Needs clarification" items={data.missingSkills} tone="clarify" />
          <ChipGroup label="Keywords found in resume" items={data.keywordsFound} tone="neutral" />
        </div>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 7. Responsibilities
// ---------------------------------------------------------------------

function ResponsibilityRows({ items, kind }: { items: string[]; kind: 'matched' | 'clarify' }) {
  if (items.length === 0) return null;
  return (
    <ul className="divide-y divide-line-soft rounded-md border border-line">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2.5 px-3 py-2.5 text-sm leading-snug text-ink">
          {kind === 'matched' ? (
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-success-600" aria-label="Matched" />
          ) : (
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning-600" aria-label="Needs clarification" />
          )}
          <span className="min-w-0 break-words">{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function ResponsibilitiesCard({ data }: { data: EvaluationData }) {
  const hasAny = data.matchedResponsibilities.length + data.missingResponsibilities.length > 0;
  return (
    <SectionCard title="Responsibilities">
      {!data.evaluated || !hasAny ? (
        <NotEvaluated text={data.evaluated ? 'No responsibilities were compared for this job.' : 'Available once the candidate has been evaluated.'} />
      ) : (
        <div className="space-y-4">
          {data.matchedResponsibilities.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-faint">Matched</p>
              <ResponsibilityRows items={data.matchedResponsibilities} kind="matched" />
            </div>
          )}
          {data.missingResponsibilities.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-faint">Needs clarification</p>
              <ResponsibilityRows items={data.missingResponsibilities} kind="clarify" />
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 8. Experience
// ---------------------------------------------------------------------

export function ExperienceCard({ data }: { data: EvaluationData }) {
  const summary = summarizeExperience(data.experience);
  return (
    <SectionCard title="Experience">
      {!data.evaluated || !summary ? (
        <NotEvaluated text={data.evaluated ? 'No experience information was found.' : 'Available once the candidate has been evaluated.'} />
      ) : (
        <div className="max-w-sm space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-ink-soft">Candidate</span>
            <span className="font-medium text-ink">{summary.candidate}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-ink-soft">Required</span>
            <span className="font-medium text-ink">{summary.required}</span>
          </div>
          <div className="pt-1">
            <Badge tone={summary.tone}>
              {summary.tone === 'success' && <Check className="h-3 w-3" />}
              {summary.tone === 'warning' && <AlertTriangle className="h-3 w-3" />}
              {summary.label}
            </Badge>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 9. Strengths
// ---------------------------------------------------------------------

function preview(items: string[], count = 3): string {
  const shown = items.slice(0, count).join(', ');
  const rest = items.length - count;
  return rest > 0 ? `${shown} and ${rest} more` : shown;
}

export function StrengthsCard({ data }: { data: EvaluationData }) {
  const { strengths } = data;
  const lines: { title: string; text: string }[] = [];

  strengths.other.forEach((item) => lines.push({ title: item, text: '' }));
  if (strengths.skills.length > 0) {
    lines.push({
      title: `${strengths.skills.length} required ${strengths.skills.length === 1 ? 'skill' : 'skills'} matched`,
      text: preview(strengths.skills),
    });
  }
  if (strengths.responsibilities.length > 0) {
    lines.push({
      title: `${strengths.responsibilities.length} job ${strengths.responsibilities.length === 1 ? 'responsibility' : 'responsibilities'} covered`,
      text: preview(strengths.responsibilities, 2),
    });
  }
  if (strengths.keywords.length > 0) {
    lines.push({
      title: 'Resume language fits the role',
      text: preview(strengths.keywords, 4),
    });
  }

  return (
    <SectionCard title="Strengths">
      {!data.evaluated || lines.length === 0 ? (
        <EmptyState
          title={data.evaluated ? 'No standout strengths recorded' : 'Strengths appear after evaluation'}
          description={data.evaluated ? undefined : 'Run an evaluation to see where this candidate is strongest.'}
        />
      ) : (
        <ul className="space-y-3">
          {lines.map((line) => (
            <li key={line.title} className="flex items-start gap-2.5">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-success-600" />
              <div className="min-w-0 text-sm">
                <p className="font-medium text-ink">{line.title}</p>
                {line.text && <p className="break-words text-ink-soft">{line.text}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

// ---------------------------------------------------------------------
// 10. Areas to Clarify
// ---------------------------------------------------------------------

export function ClarifyCard({
  data,
  onAskCandidate,
  canAsk,
}: {
  data: EvaluationData;
  onAskCandidate?: (topics: string[]) => void;
  canAsk: boolean;
}) {
  const topics = [...data.missingSkills, ...data.missingResponsibilities];
  const hasAny = topics.length + data.keywordsMissing.length > 0;

  return (
    <SectionCard
      title="Areas to Clarify"
      action={
        data.evaluated && topics.length > 0 && onAskCandidate ? (
          <Button
            size="sm"
            variant="secondary"
            icon={<MessageSquarePlus className="h-3.5 w-3.5" />}
            disabled={!canAsk}
            title={canAsk ? undefined : 'Run an evaluation first'}
            onClick={() => onAskCandidate(topics)}
          >
            Ask candidate about these
          </Button>
        ) : undefined
      }
    >
      {!data.evaluated ? (
        <NotEvaluated text="Available once the candidate has been evaluated." />
      ) : !hasAny ? (
        <div className="flex items-center gap-2 text-sm text-ink-soft">
          <Check className="h-4 w-4 text-success-600" />
          Nothing to clarify — every required skill and responsibility was found in the resume.
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-ink-soft">
            The resume doesn't show clear evidence for these. Asking the candidate for more details can settle
            them before you decide.
          </p>
          <ChipGroup label="Skills" items={data.missingSkills} tone="clarify" />
          {data.missingResponsibilities.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-faint">Responsibilities</p>
              <ResponsibilityRows items={data.missingResponsibilities} kind="clarify" />
            </div>
          )}
          <ChipGroup label="Keywords not found" items={data.keywordsMissing} tone="neutral" />
        </div>
      )}
    </SectionCard>
  );
}
