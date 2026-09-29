import { useNavigate } from 'react-router-dom';
import type { ApplicationRead } from '../../types';
import { asList, asRecord, summarizeExperience } from '../../lib/format';
import type { ExperienceResult } from '../../types';
import { Avatar, Button, EvalStatusBadge, ScorePill, SkillChip, StageBadge } from '../Primitives';

/** Current evaluation snapshot for every candidate on a job. */
export function EvaluationResultsTable({ applications }: { applications: ApplicationRead[] }) {
  const navigate = useNavigate();
  const rows = applications
    .slice()
    .sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1));

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[820px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-medium uppercase tracking-wide text-ink-faint">
            <th className="py-2.5 pr-3 font-medium">Candidate</th>
            <th className="px-3 py-2.5 font-medium">Score</th>
            <th className="px-3 py-2.5 font-medium">Evaluation Status</th>
            <th className="px-3 py-2.5 font-medium">Pipeline Stage</th>
            <th className="px-3 py-2.5 font-medium">Experience</th>
            <th className="px-3 py-2.5 font-medium">Skills</th>
            <th className="py-2.5 pl-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((app) => {
            const evaluated = app.evaluation_status === 'Completed';
            const exp = evaluated ? summarizeExperience(asRecord(app.experience_result) as ExperienceResult) : null;
            const matched = asList(app.matched_skills);
            const missing = asList(app.missing_skills);
            return (
              <tr key={app.application_id} className="hover:bg-slate-50/70">
                <td className="py-3 pr-3">
                  <div className="flex items-center gap-2.5">
                    <Avatar name={app.candidate_name} size={30} />
                    <div>
                      <p className="font-medium text-ink">{app.candidate_name}</p>
                      <p className="text-xs text-ink-faint">{app.candidate_email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-3">
                  <ScorePill score={app.overall_score} />
                </td>
                <td className="px-3 py-3">
                  <EvalStatusBadge status={app.evaluation_status} />
                </td>
                <td className="px-3 py-3">
                  <StageBadge stage={app.pipeline_stage} />
                </td>
                <td className="px-3 py-3 text-ink-soft">
                  {exp ? (
                    <>
                      <span className="text-ink">{exp.candidate}</span>
                      <span className="block text-xs text-ink-faint">{exp.label}</span>
                    </>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="max-w-[240px] px-3 py-3">
                  {evaluated && matched.length + missing.length > 0 ? (
                    <div className="flex flex-wrap items-center gap-1">
                      <SkillChip tone="matched">{matched.length} matched</SkillChip>
                      {missing.length > 0 && <SkillChip tone="clarify">{missing.length} to clarify</SkillChip>}
                    </div>
                  ) : (
                    <span className="text-ink-faint">—</span>
                  )}
                </td>
                <td className="py-3 pl-3 text-right">
                  <Button size="sm" variant="secondary" onClick={() => navigate(`/applications/${app.application_id}`)}>
                    View evaluation
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
