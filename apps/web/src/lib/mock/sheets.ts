/**
 * Sample raid totals for the static preview, in the API's RaidHeadline shape. Every name and number is made up;
 * the preview is public, so never copy anything from the guild's real sheets in here.
 */
import type { RaidHeadline } from '$lib/sheets';

const raid = (r: Partial<RaidHeadline> & Pick<RaidHeadline, 'raid_date'>): RaidHeadline => ({
  raid_day: 'wed',
  title: null,
  zone: 'BT / Hyjal',
  report_code: null,
  log_valid: true,
  characters: 25,
  clear_times: [],
  consumables_avg: null,
  low_consumables: [],
  gear_issues: null,
  players_with_gear_issues: null,
  drums: null,
  potions: null,
  interrupts: null,
  deaths: null,
  avoidable_damage: null,
  ...r
});

/** Newest first, as /api/raid-sheets/trend returns them. */
export const sheetTrend: RaidHeadline[] = [
  raid({
    raid_date: '2026-09-23',
    title: 'BT / Hyjal (BT in 1:48:32, MH in 1:08:40)',
    report_code: 'hOpPy7ToAdFr0g25',
    characters: 27,
    clear_times: [
      { zone: 'BT', seconds: 6512 },
      { zone: 'MH', seconds: 4120 }
    ],
    consumables_avg: 0.9372,
    low_consumables: ['Croakley', 'Lilypadma'],
    gear_issues: 40,
    players_with_gear_issues: 21,
    drums: 212,
    potions: 318,
    interrupts: 146,
    deaths: 157,
    avoidable_damage: 2_431_905
  }),
  raid({
    raid_date: '2026-09-16',
    title: 'BT / Hyjal (BT in 1:55:10, MH in 1:12:05)',
    report_code: 'RibB1tR1bb1tWart',
    characters: 26,
    clear_times: [
      { zone: 'BT', seconds: 6910 },
      { zone: 'MH', seconds: 4325 }
    ],
    consumables_avg: 0.9214,
    low_consumables: ['Croakley', 'Tadpolenko', 'Bufo Baggins'],
    gear_issues: 46,
    players_with_gear_issues: 23,
    drums: 198,
    potions: 301,
    interrupts: 139,
    deaths: 169,
    avoidable_damage: 2_702_118
  }),
  raid({
    raid_date: '2026-09-09',
    title: 'BT / Hyjal (BT in 2:03:47, MH in 1:15:31)',
    report_code: 'L3apFr0gP0nd2026',
    characters: 25,
    clear_times: [
      { zone: 'BT', seconds: 7427 },
      { zone: 'MH', seconds: 4531 }
    ],
    consumables_avg: 0.9018,
    low_consumables: ['Tadpolenko', 'Warty McWartface', 'Hopsalot'],
    gear_issues: 52,
    players_with_gear_issues: 24,
    drums: 187,
    potions: 288,
    interrupts: 121,
    deaths: 188,
    avoidable_damage: 3_015_440
  }),
  raid({
    raid_date: '2026-09-02',
    title: 'BT / Hyjal (BT in 2:11:20, MH in 1:21:02)',
    // Warcraft Logs had not finished processing; the sheet ran without the validation tab passing.
    report_code: 'Cr0akCr0akSw4mp1',
    log_valid: false,
    clear_times: [
      { zone: 'BT', seconds: 7880 },
      { zone: 'MH', seconds: 4862 }
    ],
    consumables_avg: 0.8871,
    low_consumables: ['Tadpolenko', 'Warty McWartface', 'Hopsalot', 'Toadally Tanked'],
    gear_issues: 61,
    players_with_gear_issues: 25,
    drums: 170,
    potions: 264,
    interrupts: 117,
    deaths: 204,
    avoidable_damage: 3_388_907
  }),
  raid({
    raid_date: '2026-08-26',
    title: 'Hyjal (MH in 1:24:48)',
    zone: 'Hyjal',
    report_code: null,
    clear_times: [{ zone: 'MH', seconds: 5088 }],
    consumables_avg: null,
    gear_issues: 38,
    players_with_gear_issues: 19,
    drums: 96,
    potions: 140,
    interrupts: null,
    deaths: 97,
    avoidable_damage: 1_204_553
  })
];
