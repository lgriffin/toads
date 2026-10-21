/**
 * The preview's awards: sample data in the browser only, so the awards desk and Me page work on GitHub Pages with no
 * hub behind them. Changes last until the page reloads.
 */
import type { MemberEntry } from '$lib/api';
import { awardable, type AwardIn, type AwardOut, type AwardsBackend } from '$lib/awards';
import { ApiError } from '$lib/api';

/** The preview's members; Hopscotch is the preview visitor. */
export const PREVIEW_MEMBERS: MemberEntry[] = [
  { member_id: 1, display_name: 'Hopscotch', discord_user_id: null },
  { member_id: 2, display_name: 'Lilypadd', discord_user_id: null },
  { member_id: 3, display_name: 'Ribbit', discord_user_id: null },
  { member_id: 4, display_name: 'Croak', discord_user_id: null },
  { member_id: 5, display_name: 'Bogwort', discord_user_id: null }
];

const SEED: [number, string, string | null, string | null, string][] = [
  [1, 'raider-of-the-week', '2026-W42', 'Never left the pad on Vashj.', '2026-10-19T21:00:00Z'],
  [2, 'floor-inspector', '2026-W42', 'Eleven deaths, four of them before the pull.', '2026-10-19T21:00:00Z'],
  [3, 'sunder-king', '2026-W42', null, '2026-10-19T21:00:00Z'],
  [4, 'brew-break', '2026-W41', 'Earl Grey, on the Lurker pull.', '2026-10-12T21:00:00Z'],
  [1, 'raider-of-the-month', '2026-09', 'Top consumable uptime on every Vashj pull.', '2026-10-01T09:00:00Z'],
  [1, 'raids-50', null, null, '2026-09-28T21:30:00Z'],
  [1, 'veteran-tbc', null, null, '2026-09-20T12:00:00Z'],
  [1, 'veteran-fresh', null, null, '2026-09-20T12:00:00Z'],
  [1, 'level-60', null, null, '2026-09-18T20:00:00Z'],
  [1, 'banker', null, 'Runs the Wednesday bank queue.', '2026-09-10T18:00:00Z'],
  [2, 'alt-60', null, 'Second sixty: a resto shaman.', '2026-10-12T22:10:00Z'],
  [2, 'raids-20', null, null, '2026-10-05T23:00:00Z'],
  [3, 'scarab-lord', null, 'Banged the gong.', '2026-09-30T19:00:00Z'],
  [4, 'wipe-veteran', null, 'Forty pulls on Kael’thas and still smiling.', '2026-10-08T23:50:00Z'],
  [5, 'master-angler', null, null, '2026-10-02T17:00:00Z']
];

let rows: AwardOut[] = SEED.map(([member_id, award_id, period, note, awarded_at], i) => ({
  id: i + 1,
  award_id,
  name: awardable(award_id)?.name ?? award_id,
  kind: awardable(award_id)?.kind ?? 'achievement',
  member_id,
  member_name: PREVIEW_MEMBERS.find((m) => m.member_id === member_id)?.display_name ?? '',
  period,
  note,
  awarded_at
}));

const newestFirst = (a: AwardOut, b: AwardOut) => b.awarded_at.localeCompare(a.awarded_at) || b.id - a.id;

export function previewAwardsOf(memberId: number): AwardOut[] {
  return rows.filter((r) => r.member_id === memberId).sort(newestFirst);
}

export const previewAwards: AwardsBackend = {
  async wall() {
    return [...rows].sort(newestFirst);
  },
  async members() {
    return PREVIEW_MEMBERS;
  },
  async give(body: AwardIn) {
    const a = awardable(body.award_id);
    if (!a) throw new ApiError(422, 'Unknown award');
    const period = body.period?.trim() || null;
    if (a.monthly && !period) throw new ApiError(422, 'Say which month this is for, as YYYY-MM');
    if (a.weekly && !/^\d{4}-W\d{2}$/.test(period ?? '')) {
      throw new ApiError(422, 'Say which raid week this is for, as YYYY-Www');
    }
    if (rows.some((r) => r.member_id === body.member_id && r.award_id === a.id && r.period === period)) {
      throw new ApiError(409, `They already hold ${a.name}${period ? ` for ${period}` : ''}`);
    }
    const row: AwardOut = {
      id: Math.max(0, ...rows.map((r) => r.id)) + 1,
      award_id: a.id,
      name: a.name,
      kind: a.kind,
      member_id: body.member_id,
      member_name: PREVIEW_MEMBERS.find((m) => m.member_id === body.member_id)?.display_name ?? '',
      period: a.monthly || a.weekly ? period : null,
      note: body.note?.trim() || null,
      awarded_at: new Date().toISOString()
    };
    rows = [...rows, row];
    return row;
  },
  async takeBack(id: number) {
    if (!rows.some((r) => r.id === id)) throw new ApiError(404, 'No such award');
    rows = rows.filter((r) => r.id !== id);
  }
};
