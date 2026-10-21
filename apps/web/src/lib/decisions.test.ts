import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import {
  consequence,
  decisionError,
  hubDecisions,
  noteAuthor,
  outcome,
  rolesLine,
  type DecisionApplication
} from './decisions';
import { previewDecisions } from './preview/decisions-fake';

const app: DecisionApplication = {
  id: 7,
  applicant_name: 'Newtonian',
  character_name: 'Mossbeard',
  class_name: 'Shaman',
  role: 'Healer',
  secondary_role: 'Ranged',
  why_toads: '',
  raid_days: ['wed'],
  logs_url: null,
  status: 'interviewing',
  interview_room_error: null,
  interview_room_url: 'https://discord.com/channels/1/2',
  created_at: '2026-10-20T18:00:00Z'
};

describe('decisions panel', () => {
  it('says what each decision does before it is confirmed', () => {
    expect(consequence('reject', app, 'Wednesday')).toBe(
      'Mossbeard is declined and the Toad Bot deletes their interview room. They can apply again in 30 days.'
    );
    expect(consequence('accept', app, 'Wednesday')).toBe(
      'Mossbeard joins Wednesday: the Toad Bot gives them the Wednesday raider role in Discord and welcomes them in their room.'
    );
    const roomless = { ...app, interview_room_url: null };
    expect(consequence('reject', roomless, 'Wednesday')).not.toContain('room');
    expect(consequence('accept', roomless, 'Wednesday')).not.toContain('room');
  });

  it('reads roles, authors and outcomes in words', () => {
    expect(rolesLine(app)).toBe('Healer, then Ranged');
    expect(rolesLine({ ...app, secondary_role: null })).toBe('Healer');
    expect(noteAuthor({ id: 1, application_id: 7, author_name: null, body: '', at: '' })).toBe('Toad Bot');
    expect(noteAuthor({ id: 1, application_id: 7, author_name: 'Hadur', body: '', at: '' })).toBe('Hadur');
    expect([outcome('accepted'), outcome('declined'), outcome('withdrawn')]).toEqual([
      'Accepted',
      'Rejected',
      'Withdrawn by the applicant'
    ]);
  });

  it('calls the night’s routes', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({})));
    const hub = hubDecisions(f as unknown as typeof fetch);
    await hub.board('sun');
    await hub.note('sun', 7, 'Good logs');
    await hub.decide('sun', 7, 'reject');
    const calls = f.mock.calls as unknown as [string, RequestInit][];
    expect(calls.map(([p, i]) => [i?.method ?? 'GET', p, i?.body])).toEqual([
      ['GET', '/api/days/sun/admin/decisions', undefined],
      ['POST', '/api/days/sun/admin/applications/7/notes', '{"body":"Good logs"}'],
      ['POST', '/api/days/sun/admin/applications/7/decision', '{"decision":"reject"}']
    ]);
  });

  it('explains refusals', () => {
    expect(decisionError(new ApiError(403, 'Forbidden'))).toContain('officers');
    expect(decisionError(new ApiError(409, 'This application is already accepted'))).toBe(
      'This application is already accepted'
    );
    expect(decisionError(new Error('boom'))).toBe('Something went wrong; try again.');
  });

  it('keeps the preview’s decisions per night', async () => {
    const preview = previewDecisions();
    const wed = await preview.board('wed');
    expect(wed.waiting.map((c) => c.application.character_name)).toEqual(['Mossbeard', 'Big Toad']);
    await preview.decide('wed', 2, 'reject');
    expect((await preview.board('wed')).decided.map((c) => c.application.status)).toContain('declined');
    await expect(preview.note('wed', 2, 'late')).rejects.toMatchObject({ status: 409 });
    await expect(preview.decide('sun', 1, 'accept')).rejects.toMatchObject({ status: 404 });
  });
});
