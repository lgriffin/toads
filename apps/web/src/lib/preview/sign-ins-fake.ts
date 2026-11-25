/**
 * The preview's sign-in audit: sample sign-ins in the browser only, so the officers' Sign-ins page works on GitHub Pages
 * with no hub behind it. Times are counted back from now so the sample never goes stale.
 */
import { ApiError } from '$lib/api';
import { isoDay, shiftDay, type SignInDay, type SignInsBackend } from '$lib/sign-ins';

// name, night (null: on no raid night), the days ago each sign-in happened (fractions are hours), never signed in
const PEOPLE: [string, string | null, number[]][] = [
  ['Hopscotch', 'wed', [0.1, 1.3, 3.2, 7.4]],
  ['Ribbit', 'wed', [0.3, 2.1, 9.5]],
  ['Croak', 'wed', [1.2, 5.6]],
  ['Lilypad', 'wed', [21.4]],
  ['Bullrush', 'wed', []],
  ['Puddle', 'sun', [0.2, 4.4]],
  ['Marsh', 'sun', [6.3]],
  ['Mossback', 'sun', []],
  ['Tadpole', null, [0.4, 12.2]]
];

const at = (daysAgo: number) => new Date(Date.now() - daysAgo * 86_400_000);

function view(day: string | null, on: string): SignInDay {
  const mine = PEOPLE.map((p, i) => ({ id: i + 1, name: p[0], night: p[1], times: p[2].map(at) })).filter(
    (p) => p.night === day
  );
  const all = mine.flatMap((p) => p.times.map((t) => ({ member_id: p.id, member_name: p.name, at: t })));
  const recent = Array.from({ length: 14 }, (_, n) => {
    const date = shiftDay(on, -n);
    const those = all.filter((s) => isoDay(s.at) === date);
    return { date, sign_ins: those.length, members: new Set(those.map((s) => s.member_id)).size };
  });
  return {
    raid_day: day,
    date: on,
    sign_ins: all
      .filter((s) => isoDay(s.at) === on)
      .sort((a, b) => b.at.getTime() - a.at.getTime())
      .map((s) => ({ ...s, at: s.at.toISOString() })),
    members: mine
      .filter((p) => day !== null || p.times.length)
      .map((p) => ({ member_id: p.id, member_name: p.name, last: p.times[0] ?? null }))
      .sort((a, b) => (b.last?.getTime() ?? -Infinity) - (a.last?.getTime() ?? -Infinity))
      .map((p) => ({ member_id: p.member_id, member_name: p.member_name, last_signed_in_at: p.last?.toISOString() ?? null })),
    recent
  };
}

export const previewSignIns: SignInsBackend = {
  async day(day, on) {
    const today = isoDay(new Date());
    const chosen = on ?? today;
    if (chosen > today) throw new ApiError(422, 'That day has not happened yet');
    return view(day, chosen);
  }
};
