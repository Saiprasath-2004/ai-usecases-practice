import api from './client';
import type { ApplicationBoard, JobCreate, JobRead } from '../types';

export async function listJobs(): Promise<JobRead[]> {
  const { data } = await api.get('/jobs');
  return data;
}

export async function getJob(jobId: number): Promise<JobRead> {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data;
}

export async function createJob(payload: JobCreate): Promise<JobRead> {
  const { data } = await api.post('/jobs', payload);
  return data;
}

/** Grouped by pipeline stage, sorted by score — the shape the candidate table renders directly. */
export async function listJobApplications(jobId: number): Promise<ApplicationBoard> {
  const { data } = await api.get(`/jobs/${jobId}/applications`);
  return data.applications as ApplicationBoard;
}

/**
 * Fire-and-forget: the backend runs this via BackgroundTasks and returns
 * immediately. There is no progress/webhook — callers must poll
 * listJobApplications() and watch evaluation_status settle.
 */
export async function triggerBulkEvaluation(jobId: number): Promise<{ status: string; message?: string }> {
  const { data } = await api.post(`/jobs/${jobId}/evaluations`);
  return data;
}
