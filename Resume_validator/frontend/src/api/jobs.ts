import api from './client';
import type { ApplicationBoard, JobRead } from '../types';

export async function createJobFromInput(payload?: {
  title?: string;
  department?: string;
  location?: string;
  employment_type?: string;
  job_description_text?: string;
  job_description_source?: string;
  required_skills?: string;
}): Promise<JobRead> {
  const jdPath = payload?.job_description_source || 'data/jd.txt';
  const response = await fetch(`http://localhost:8000/jobs`);
  let existingJob: JobRead | null = null;
  try {
    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      existingJob = data[0];
    }
  } catch {
    // ignore
  }

  const jobPayload = {
    title: payload?.title || existingJob?.title || 'AI Platform Engineer',
    department: payload?.department || existingJob?.department || 'Engineering',
    location: payload?.location || existingJob?.location || 'Remote',
    employment_type: payload?.employment_type || existingJob?.employment_type || 'Full-time',
    job_description_text: payload?.job_description_text || existingJob?.job_description_text || 'Sample job description',
    job_description_source: payload?.job_description_source || existingJob?.job_description_source || jdPath,
    required_skills: payload?.required_skills || existingJob?.job_description_source ? '[]' : '[]',
  };

  const { data } = await api.post('/jobs', jobPayload);
  return data;
}

export async function listJobs(): Promise<JobRead[]> {
  const { data } = await api.get('/jobs');
  return data;
}

export async function getJob(jobId: number): Promise<JobRead> {
  const { data } = await api.get(`/jobs/${jobId}`);
  return data;
}

export async function listJobApplications(jobId: number): Promise<ApplicationBoard> {
  const { data } = await api.get(`/jobs/${jobId}/applications`);
  return data.applications as ApplicationBoard;
}

export async function triggerBulkEvaluation(jobId: number): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/jobs/${jobId}/evaluations`);
  return data;
}
