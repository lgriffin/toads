import { describe, expect, it } from 'vitest';
import { APPLICATION_STATUSES, canTransition, isFinal, nextActions, type ApplicationStatus } from './recruitment';

const ALLOWED = new Set([
  'applied>interviewing',
  'applied>declined',
  'applied>withdrawn',
  'interviewing>trial_offered',
  'interviewing>declined',
  'interviewing>withdrawn',
  'trial_offered>accepted',
  'trial_offered>declined',
  'trial_offered>withdrawn'
]);

const pairs = APPLICATION_STATUSES.flatMap((from) => APPLICATION_STATUSES.map((to) => [from, to] as const));

describe('canTransition', () => {
  it('covers all 36 pairs', () => expect(pairs).toHaveLength(36));
  it.each(pairs)('%s -> %s', (from, to) => {
    expect(canTransition(from, to)).toBe(ALLOWED.has(`${from}>${to}`));
  });
  it('rejects unknown statuses', () => {
    expect(canTransition('hired' as ApplicationStatus, 'accepted')).toBe(false);
  });
});

describe('nextActions', () => {
  it.each(APPLICATION_STATUSES)('%s offers officers exactly the allowed transitions', (status) => {
    const tos = nextActions(status).map((a) => a.to);
    // Withdrawing is the applicant's own action; officers never get that button.
    expect(tos).toEqual(APPLICATION_STATUSES.filter((to) => to !== 'withdrawn' && ALLOWED.has(`${status}>${to}`)));
    expect(isFinal(status)).toBe(tos.length === 0);
  });
  it('labels the interview room and marks decline as dangerous', () => {
    const actions = nextActions('applied');
    expect(actions[0]).toEqual({ to: 'interviewing', label: 'Open interview room', tone: 'primary' });
    expect(actions.find((a) => a.to === 'declined')?.tone).toBe('danger');
    expect(nextActions('trial_offered').map((a) => a.label)).toEqual(['Accept', 'Decline']);
  });
});
