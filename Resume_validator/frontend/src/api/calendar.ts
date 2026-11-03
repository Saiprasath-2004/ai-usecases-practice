import api from './client';
import type {
  AvailabilityCreate,
  AvailabilityRead,
  AvailabilityUpdate,
  AvailableSlotsResponse,
  CalendarBlockCreate,
  CalendarBlockRead,
  FullDayBlockCreate,
  InterviewCreate,
  InterviewRead,
} from '../types';

export async function listAvailability(recruiterId: string): Promise<AvailabilityRead[]> {
  const { data } = await api.get('/calendar/availability', { params: { recruiter_id: recruiterId } });
  return data;
}

export async function createAvailability(payload: AvailabilityCreate): Promise<AvailabilityRead> {
  const { data } = await api.post('/calendar/availability', payload);
  return data;
}

export async function updateAvailability(
  availabilityId: number,
  payload: AvailabilityUpdate,
): Promise<AvailabilityRead> {
  const { data } = await api.put(`/calendar/availability/${availabilityId}`, payload);
  return data;
}

export async function deleteAvailability(availabilityId: number): Promise<void> {
  await api.delete(`/calendar/availability/${availabilityId}`);
}

export async function listBlocks(recruiterId: string): Promise<CalendarBlockRead[]> {
  const { data } = await api.get('/calendar/blocks', { params: { recruiter_id: recruiterId } });
  return data;
}

export async function createBlock(payload: CalendarBlockCreate): Promise<CalendarBlockRead> {
  const { data } = await api.post('/calendar/blocks', payload);
  return data;
}

export async function createFullDayBlock(payload: FullDayBlockCreate): Promise<CalendarBlockRead> {
  const { data } = await api.post('/calendar/blocks/full-day', payload);
  return data;
}

export async function deleteBlock(blockId: number): Promise<void> {
  await api.delete(`/calendar/blocks/${blockId}`);
}

export async function getAvailableSlots(
  recruiterId: string,
  targetDate: string,
  durationMinutes = 60,
): Promise<AvailableSlotsResponse> {
  const { data } = await api.get('/calendar/slots', {
    params: { recruiter_id: recruiterId, target_date: targetDate, duration_minutes: durationMinutes },
  });
  return data;
}

/** Manual booking path — bypasses the natural-language flow in /applications/{id}/review. */
export async function createInterview(payload: InterviewCreate): Promise<InterviewRead> {
  const { data } = await api.post('/calendar/interviews', payload);
  return data;
}
