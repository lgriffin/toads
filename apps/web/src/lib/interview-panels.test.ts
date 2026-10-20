import { describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import { hubPanels, notOnPanel, panelError, whoInterviews, type Interviewer } from './interview-panels';
import { previewPanels } from './preview/panels-fake';

const gal: Interviewer = { discord_user_id: '301', username: '_gallagher', display_name: 'Gallagher' };
const hadur: Interviewer = { discord_user_id: '302', username: 'hadur117', display_name: 'Hadur' };

describe('interview panels', () => {
  it('says who meets the night’s applicants', () => {
    expect(whoInterviews({ raid_day: 'sun', interviewers: [gal, hadur], fallback: [] }, 'Sunday')).toBe(
      'Everyone who applies for Sunday gets a private room with these 2 interviewers.'
    );
    expect(whoInterviews({ raid_day: 'sun', interviewers: [], fallback: ['_gallagher'] }, 'Sunday')).toContain(
      'set on the server: _gallagher'
    );
    expect(whoInterviews({ raid_day: 'sun', interviewers: [], fallback: [] }, 'Sunday')).toContain('an officer');
  });

  it('leaves people already on the panel out of the search results', () => {
    expect(notOnPanel([gal, hadur], [gal])).toEqual([hadur]);
  });

  it('calls the night’s routes', async () => {
    const f = vi.fn(async () => new Response(JSON.stringify({ raid_day: 'sun', interviewers: [], fallback: [] })));
    const hub = hubPanels(f as unknown as typeof fetch);
    await hub.add('sun', '302');
    await hub.remove('sun', '302');
    await hub.search('sun', 'had ur');
    expect((f.mock.calls as unknown as [string, RequestInit][]).map(([p, i]) => [i?.method ?? 'GET', p])).toEqual([
      ['POST', '/api/days/sun/admin/interview-panel'],
      ['DELETE', '/api/days/sun/admin/interview-panel/302'],
      ['GET', '/api/days/sun/admin/discord-members?q=had%20ur']
    ]);
  });

  it('explains refusals', () => {
    expect(panelError(new ApiError(403, 'Forbidden'))).toContain('officers');
    expect(panelError(new ApiError(409, 'Hadur is already on this night\'s panel'))).toBe(
      'Hadur is already on this night\'s panel'
    );
    expect(panelError(new Error('x'))).toBe('Something went wrong; try again.');
  });

  it('works in the preview with no hub', async () => {
    const fake = previewPanels();
    expect((await fake.add('sun', '302')).interviewers).toEqual([hadur]);
    await expect(fake.add('sun', '302')).rejects.toThrow('already');
    expect((await fake.remove('sun', '302')).interviewers).toEqual([]);
    expect(await fake.search('sun', 'HAD')).toEqual([hadur]);
  });
});
