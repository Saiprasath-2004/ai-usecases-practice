import { FileText, PlayCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { ApplicationRead } from '../../types';
import { asList } from '../../lib/format';
import { Avatar, Button, EvalStatusBadge, ScorePill, StageBadge } from '../Primitives';

export function CandidateTable({
  applications,
  onEvaluate,
  evaluatingId,
  showJobColumn = false,
  jobTitleFor,
}: {
  applications: ApplicationRead[];
  onEvaluate?: (applicationId: string) => void;
  evaluatingId?: string | null;
  showJobColumn?: boolean;
  jobTitleFor?: (applicationId: string) => string | undefined;
}) {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[860px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs font-medium uppercase tracking-wide text-ink-faint">
            <th className="py-2.5 pr-3 font-medium">Candidate</th>
            {showJobColumn && <th className="px-3 py-2.5 font-medium">Job</th>}
            <th className="px-3 py-2.5 font-medium">Skills</th>
            <th className="px-3 py-2.5 font-medium">ATS Score</th>
            <th className="px-3 py-2.5 font-medium">Pipeline Stage</th>
            <th className="px-3 py-2.5 font-medium">Evaluation</th>
            <th className="px-3 py-2.5 font-medium">Resume</th>
            <th className="py-2.5 pl-3 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {applications.map((app) => {
            const skills = asList(app.matched_skills);
            const isEvaluating = evaluatingId === app.application_id || app.evaluation_status === 'Running';
            return (
              <tr key={app.application_id} className="hover:bg-slate-50/70">
                <td className="py-3 pr-3">
                  <button
                    onClick={() => navigate(`/applications/${app.application_id}`)}
                    className="focus-ring flex items-center gap-2.5 rounded text-left"
                  >
                    <Avatar name={app.candidate_name} size={30} />
                    <span>
                      <span className="block font-medium text-ink">{app.candidate_name}</span>
                      <span className="block text-xs text-ink-faint">{app.candidate_email}</span>
                    </span>
                  </button>
                </td>
                {showJobColumn && (
                  <td className="px-3 py-3 text-ink-soft">{jobTitleFor?.(app.application_id) ?? '—'}</td>
                )}
                <td className="max-w-[220px] px-3 py-3">
                  {skills.length === 0 ? (
                    <span className="text-ink-faint">—</span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {skills.slice(0, 3).map((s) => (
                        <span
                          key={s}
                          className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-ink-soft"
                        >
                          {s}
                        </span>
                      ))}
                      {skills.length > 3 && (
                        <span className="text-xs text-ink-faint">+{skills.length - 3}</span>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-3 py-3">
                  <ScorePill score={app.overall_score} />
                </td>
                <td className="px-3 py-3">
                  <StageBadge stage={app.pipeline_stage} />
                </td>
                <td className="px-3 py-3">
                  <EvalStatusBadge status={app.evaluation_status} />
                </td>
                <td className="px-3 py-3">
                  {app.resume_path ? (
                    <span className="inline-flex items-center gap-1 text-ink-soft">
                      <FileText className="h-3.5 w-3.5" />
                      <span className="max-w-[110px] truncate text-xs">{app.resume_path.split('/').pop()}</span>
                    </span>
                  ) : (
                    <span className="text-ink-faint">—</span>
                  )}
                </td>
                <td className="py-3 pl-3">
                  <div className="flex items-center justify-end gap-1.5">
                    {onEvaluate && app.evaluation_status !== 'Completed' && (
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<PlayCircle className="h-3.5 w-3.5" />}
                        loading={isEvaluating}
                        disabled={isEvaluating}
                        onClick={() => onEvaluate(app.application_id)}
                      >
                        {app.evaluation_status === 'Failed' ? 'Retry' : 'Evaluate'}
                      </Button>
                    )}
                    <Button size="sm" variant="primary" onClick={() => navigate(`/applications/${app.application_id}`)}>
                      Review
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
