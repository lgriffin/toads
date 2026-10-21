/** Sample answers for the hub home's Next raid and Your performance widgets, in the API's shapes, for the preview. */

import type { NextRaid } from '$lib/next-raid';
import type { MyPerformance } from '$lib/performance';
import { nextRaid as sampleRaid } from './data';

const signedUp = Object.values(sampleRaid.signups).reduce((a, b) => a + b, 0);

export const previewNextRaid: NextRaid = {
  name: sampleRaid.zone,
  starts_at: sampleRaid.start,
  ends_at: null,
  raid_day_id: 'sun',
  raid_day_name: sampleRaid.raidDay,
  source: 'discord',
  under_way: false,
  interested: signedUp,
  url: 'https://discord.com/events/1/1'
};

/** The preview's clock: two days before the sample raid, so the countdown reads as it would on a normal week. */
export const previewNow = new Date(new Date(sampleRaid.start).getTime() - 2 * 86_400_000);

export const previewPerformance: MyPerformance = {
  // The same raids as Hopscotch's sample character page on Me (mock/characters.ts), so the two agree.
  generated_at: '2026-10-16 08:00:00',
  raid: { report_id: 'pondWed1014', title: 'Serpentshrine Cavern', date: '2026-10-14' },
  entry: {
    name: 'Hopscotch',
    class: 'Rogue',
    role: 'melee',
    metric: 'Damage',
    unit: 'amount',
    value: 9_180_000,
    median: 8_060_000,
    rank: 2,
    of: 3,
    recent: [
      { date: '2026-09-30', value: 7_260_000, median: 6_970_000 },
      { date: '2026-10-04', value: 7_430_000, median: 7_100_000 },
      { date: '2026-10-07', value: 7_910_000, median: 7_710_000 },
      { date: '2026-10-11', value: 8_520_000, median: 7_640_000 },
      { date: '2026-10-14', value: 9_180_000, median: 8_060_000 }
    ]
  },
  matched_by: 'claim',
  looked_for: ['Hopscotch', 'Lilypadd']
};
