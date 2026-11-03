import type { ApplicationBoard, ApplicationRead } from '../types';

/**
 * Applications come back grouped by pipeline stage. Every screen that needs
 * a flat candidate list goes through this one function so counts can never
 * disagree between pages.
 */
export function flattenBoard(board: ApplicationBoard | ApplicationRead[] | null | undefined): ApplicationRead[] {
  if (!board) return [];
  if (Array.isArray(board)) return board;
  return Object.values(board).flatMap((group) => (Array.isArray(group) ? group : []));
}

export function isEvaluationInFlight(app: Pick<ApplicationRead, 'evaluation_status'>): boolean {
  return app.evaluation_status === 'Running';
}
