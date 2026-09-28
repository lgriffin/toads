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
  generated_at: '2026-09-25 08:00:00',
  raid: { report_id: 'ssc-0924', title: 'Serpentshrine Cavern', date: '2026-09-24' },
  entry: {
    name: 'Hopscotch',
    class: 'Rogue',
    role: 'melee',
    metric: 'Damage',
    unit: 'amount',
    value: 2_870_000,
    median: 2_430_000,
    rank: 2,
    of: 7,
    recent: [
      { date: '2026-09-10', value: 2_310_000, median: 2_280_000 },
      { date: '2026-09-13', value: 2_520_000, median: 2_390_000 },
      { date: '2026-09-17', value: 2_180_000, median: 2_350_000 },
      { date: '2026-09-20', value: 2_760_000, median: 2_410_000 },
      { date: '2026-09-24', value: 2_870_000, median: 2_430_000 }
    ]
  },
  matched_by: 'claim',
  looked_for: ['Hopscotch', 'Lilypadd']
};
