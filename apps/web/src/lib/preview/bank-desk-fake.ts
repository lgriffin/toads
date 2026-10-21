/**
 * The preview's bank request desk: sample requests as if raiders had used the Toad Bot's /bankrequest, kept in the
 * browser only, so the desk works on GitHub Pages with no hub behind it. Answers, and the DM each one sends, last until
 * the page reloads.
 */
import { ApiError } from '$lib/api';
import type { BankDeskBackend, BankRequest } from '$lib/bank-desk';

const HOPSCOTCH = '303';

const sample = (
  id: number,
  [discord_user_id, requester_name]: [string, string],
  item: string,
  quantity: number,
  created_at: string,
  answer?: Partial<BankRequest>
): BankRequest => ({
  id,
  discord_user_id,
  requester_name,
  item,
  quantity,
  source: 'discord',
  status: 'pending',
  created_at,
  officer_message: null,
  decided_by_name: null,
  decided_at: null,
  notice: null,
  notice_error: null,
  ...answer
});

const LILYPADD: [string, string] = ['304', 'Lilypadd'];
const RIBBIT: [string, string] = ['305', 'Ribbit'];
const HOP: [string, string] = [HOPSCOTCH, 'Hopscotch'];

/** `manage`: whether the preview visitor works the desk (the officer and super admin views). */
export function previewBankDesk(manage: boolean): BankDeskBackend {
  let next = 7;
  let rows: BankRequest[] = [
    sample(1, LILYPADD, 'Flask of Relentless Assault', 4, '2026-10-12T18:20:00Z', {
      status: 'approved',
      officer_message: 'Grab them from Gail before the pull.',
      decided_by_name: 'Hadur',
      decided_at: '2026-10-12T19:02:00Z',
      notice: 'sent'
    }),
    sample(2, HOP, 'Super Mana Potion', 20, '2026-10-14T09:41:00Z', {
      status: 'denied',
      officer_message: 'We are short this week; ask again after Sunday.',
      decided_by_name: 'Hadur',
      decided_at: '2026-10-14T12:15:00Z',
      notice: 'failed',
      notice_error: 'Discord refused: 403 Cannot send messages to this user'
    }),
    sample(3, RIBBIT, 'Drums of Battle', 2, '2026-10-19T20:05:00Z'),
    sample(4, LILYPADD, 'Elixir of Major Agility', 10, '2026-10-20T17:30:00Z'),
    sample(5, HOP, 'Flask of Supreme Power', 2, '2026-10-20T21:12:00Z'),
    { ...sample(6, RIBBIT, 'Primal Might', 1, '2026-10-21T07:55:00Z'), source: 'site' }
  ];
  const refuse = () => {
    if (!manage) throw new ApiError(403, 'Forbidden');
  };
  return {
    manageDays: async () => (manage ? ['wed'] : []),
    incoming: async () => {
      refuse();
      return [...rows];
    },
    history: async (_day, id) => {
      refuse();
      return rows.filter((r) => r.discord_user_id === id).sort((a, b) => b.id - a.id);
    },
    mine: async () => rows.filter((r) => r.discord_user_id === HOPSCOTCH).sort((a, b) => b.id - a.id),
    ask: async (item, quantity) => {
      const made = { ...sample(next++, HOP, item.trim(), quantity, new Date().toISOString()), source: 'site' };
      rows = [...rows, made];
      return made;
    },
    answer: async (_day, id, verdict, message) => {
      refuse();
      const row = rows.find((r) => r.id === id);
      if (!row) throw new ApiError(404, 'No such request');
      if (row.status !== 'pending') throw new ApiError(409, `That request was already ${row.status}`);
      const answered: BankRequest = {
        ...row,
        status: verdict === 'approve' ? 'approved' : 'denied',
        officer_message: message.trim() || null,
        decided_by_name: 'You',
        decided_at: new Date().toISOString(),
        // Nothing leaves the browser: the preview shows the DM as sent.
        notice: 'sent'
      };
      rows = rows.map((r) => (r.id === id ? answered : r));
      return answered;
    }
  };
}
