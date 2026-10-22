import { describe, expect, it } from 'vitest';
import { ApiError, type Claim } from './api';
import { previewSetup } from './preview/setup-fake';
import { WELCOME, altsOf, setupError, type SetupState } from './setup';

const claim = (id: number, name: string, status: Claim['status']): Claim => ({
  id,
  member_id: 7,
  character_id: id + 100,
  character_name: name,
  raid_day_id: 'wed',
  status,
  reason: null
});

const state = (over: Partial<SetupState> = {}): SetupState => ({ done: false, main: null, declared: [], main_open: true, ...over });

describe('setup', () => {
  it('welcomes from Gally and the officers to the Pond, never anything else', () => {
    expect(WELCOME.heading).toBe('Welcome to the Pond');
    expect(WELCOME.signoff).toBe('Gally and the officers');
    expect(WELCOME.body.join(' ')).toContain('Thanks for logging in');
    expect(JSON.stringify(WELCOME).toLowerCase()).not.toContain('frog');
  });

  it('lists every live claim and named character but the main as an alt', () => {
    const claims = [claim(1, 'Hopscotch', 'approved'), claim(2, 'Ribbit', 'pending'), claim(3, 'Croak', 'rejected')];
    const alts = altsOf(
      claims,
      state({
        main: { name: 'hopscotch', status: 'approved' },
        declared: [
          { id: 9, name: 'Tadpole', wow_class: 'druid', main: false },
          { id: 10, name: 'Newt', wow_class: 'mage', main: true }
        ]
      })
    );
    expect(alts.map((a) => [a.name, a.status])).toEqual([
      ['Ribbit', 'Waiting for an officer'],
      ['Tadpole', 'Waiting for its first logged raid']
    ]);
  });

  it('says why a step failed in plain words', () => {
    expect(setupError(new ApiError(409, 'Already named'))).toMatch(/already named/);
    expect(setupError(new ApiError(409, 'Ask your officers to swap your main'))).toMatch(/main swap/);
    expect(setupError(new ApiError(403, 'Forbidden'))).toMatch(/trial or raider/);
    expect(setupError(new Error('x'))).toBe('Something went wrong; try again.');
  });

  it('runs the whole setup in the preview with no hub behind it', async () => {
    const [hop] = await previewSetup.search('hop');
    await previewSetup.claim(hop.id);
    await previewSetup.setMain(hop.id);
    await previewSetup.declare('Tadpole', 'druid', false);
    expect((await previewSetup.state()).main).toEqual({ name: 'Hopscotch', status: 'pending' });
    await expect(previewSetup.declare('tadpole', 'druid', false)).rejects.toThrow('Already named');
    await previewSetup.finish();
    expect((await previewSetup.state()).done).toBe(true);
  });
});
