import api from './client';
import type { ApplicationRead, RecruiterActionType } from '../types';

export async function getApplication(applicationId: string): Promise<ApplicationRead> {
  const { data } = await api.get(`/applications/${applicationId}`);
  return data;
}

export async function performAction(
  applicationId: string,
  actionType: RecruiterActionType,
  note?: string
): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/applications/${applicationId}/actions`, {
    action_type: actionType,
    note: note || undefined,
  });
  return data;
}

// --- Stubbed backend endpoints. These currently return a placeholder
// response ({"status": "stubbed", ...}) rather than doing anything real —
// wired up here so the UI is ready the moment the backend fills them in.

export async function getInterviewSlots(applicationId: string): Promise<{ status: string; message: string }> {
  const { data } = await api.get(`/applications/${applicationId}/interview-slots`);
  return data;
}

export async function scheduleInterview(applicationId: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/applications/${applicationId}/interview`);
  return data;
}

export async function approveFollowup(applicationId: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/applications/${applicationId}/follow-up/approve`);
  return data;
}

export async function submitFollowupReplyStub(applicationId: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/applications/${applicationId}/follow-up/reply`);
  return data;
}
