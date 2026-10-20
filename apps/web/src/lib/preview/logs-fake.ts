/**
 * The preview's Logs: sample raids in the browser only, shaped like the analyzer's raid pages, so the Logs page works
 * on GitHub Pages with no hub behind it. Who sees per-player numbers follows the API: a member sees overviews, the
 * Wednesday officer view sees Wednesday raids in full, and a super admin sees everything.
 */
import { ApiError, type Session } from '$lib/api';
import type { AnalyzerPage } from '$lib/home-payload';
import type {
  BossHistory,
  Encounter,
  EncounterPlayer,
  LogsBackend,
  LogsOverview,
  RaidPage,
  RaidRow,
  RaidSummary,
  RaidView
} from '$lib/logs';
import { analyzerPage } from '$lib/mock/analyzer';
import type { PreviewRole } from './gate';

const WEDNESDAY = 2;

type Seat = [name: string, player_class: string, role: 'tanks' | 'healers' | 'melee' | 'ranged', power: number];

const ROSTER: Seat[] = [
  ['Bogwort', 'Warrior', 'tanks', 0.9],
  ['Croak', 'Paladin', 'tanks', 0.8],
  ['Lilypadd', 'Priest', 'healers', 1.1],
  ['Marshmallow', 'Druid', 'healers', 0.95],
  ['Tadpoll', 'Shaman', 'healers', 1.0],
  ['Hopscotch', 'Rogue', 'melee', 1.15],
  ['Ribbit', 'Warrior', 'melee', 1.05],
  ['Reedwhistle', 'Shaman', 'melee', 0.9],
  ['Pondweed', 'Mage', 'ranged', 1.1],
  ['Duckweed', 'Warlock', 'ranged', 1.2],
  ['Bullrush', 'Hunter', 'ranged', 1.0],
  ['Mirewisp', 'Priest', 'ranged', 0.85]
];

const ZONES: Record<string, [id: number, name: string, seconds: number][]> = {
  'Serpentshrine Cavern': [
    [623, 'Hydross the Unstable', 290],
    [624, 'The Lurker Below', 245],
    [625, 'Leotheras the Blind', 330],
    [626, 'Fathom-Lord Karathress', 300],
    [627, 'Morogrim Tidewalker', 260],
    [628, 'Lady Vashj', 620]
  ],
  'Tempest Keep': [
    [730, "Al'ar", 380],
    [731, 'Void Reaver', 230],
    [732, 'High Astromancer Solarian', 270],
    [733, "Kael'thas Sunstrider", 840]
  ]
};

// [report id, local start, zone]
const RAIDS: [string, string, string][] = [
  ['pondThu1015', '2026-10-15 20:00:00', 'Tempest Keep'],
  ['pondWed1014', '2026-10-14 19:30:00', 'Serpentshrine Cavern'],
  ['pondSun1011', '2026-10-11 19:00:00', 'Tempest Keep'],
  ['pondWed1007', '2026-10-07 19:30:00', 'Serpentshrine Cavern'],
  ['pondSun1004', '2026-10-04 19:00:00', 'Serpentshrine Cavern'],
  ['pondWed0930', '2026-09-30 19:30:00', 'Tempest Keep']
];

function weekdayOf(date: string): number {
  return (new Date(`${date.slice(0, 10)}T00:00:00Z`).getUTCDay() + 6) % 7;
}

function summaryOf([id, date, zone]: [string, string, string]): RaidSummary {
  return {
    report_id: id,
    title: `${zone.split(' ')[0]} with the toads`,
    zone,
    raid_date: date,
    weekday: weekdayOf(date),
    size: ROSTER.length,
    url: `https://fresh.warcraftlogs.com/reports/${id}`
  };
}

/** A steady wobble per raid, boss and player, so the sample reads like real numbers and never changes. */
function wobble(...keys: (string | number)[]): number {
  let h = 7;
  for (const ch of keys.join('|')) h = (h * 31 + ch.charCodeAt(0)) % 9973;
  return 0.85 + (h % 300) / 1000;
}

function encounterPlayers(raid: string, boss: number, seconds: number): EncounterPlayer[] {
  return ROSTER.map(([name, player_class, role, power]) => {
    const w = wobble(raid, boss, name);
    const dps = role === 'melee' || role === 'ranged' ? 1150 * power * w : role === 'tanks' ? 520 * power * w : 40 * w;
    const hps = role === 'healers' ? 980 * power * w : 0;
    return {
      name,
      player_class,
      role: role.replace(/s$/, ''),
      damage: Math.round(dps * seconds),
      healing: Math.round(hps * seconds),
      damage_taken: Math.round((role === 'tanks' ? 1600 : 160) * w * seconds),
      active_percent: Math.round(Math.min(99.5, 88 * w) * 10) / 10
    };
  }).sort((a, b) => b.damage - a.damage || a.name.localeCompare(b.name));
}

function encountersOf(s: RaidSummary): Encounter[] {
  return ZONES[s.zone].map(([id, name, seconds]) => {
    const length = Math.round(seconds * wobble(s.report_id, id, 'time'));
    const players = encounterPlayers(s.report_id, id, length);
    return {
      encounter_id: id,
      name,
      duration_ms: length * 1000,
      damage: players.reduce((n, p) => n + p.damage, 0),
      healing: players.reduce((n, p) => n + p.healing, 0),
      players
    };
  });
}

const CONSUMABLES = ['Flask of Relentless Assault', 'Super Mana Potion', 'Haste Potion', 'Flask of Mighty Restoration'];

function pageOf(s: RaidSummary): RaidPage {
  const encounters = encountersOf(s);
  const total = (name: string, key: 'damage' | 'healing' | 'damage_taken') =>
    encounters.reduce((n, e) => n + (e.players?.find((p) => p.name === name)?.[key] ?? 0), 0) * 1.4;
  const seats = (role: Seat[2]) => ROSTER.filter((r) => r[2] === role);
  const player = ([name, player_class]: Seat) => ({ name, player_class });
  const dps = (role: Seat[2]) =>
    seats(role)
      .map((r) => ({ ...player(r), damage: Math.round(total(r[0], 'damage')), active_percent: Math.min(99, Math.round(90 * wobble(s.report_id, r[0]))) }))
      .sort((a, b) => b.damage - a.damage);
  return {
    version: 1,
    summary: s,
    duration_ms: encounters.reduce((n, e) => n + e.duration_ms, 0) * 3,
    warnings: [],
    composition: {
      tanks: seats('tanks').map(player),
      healers: seats('healers').map(player),
      melee: seats('melee').map(player),
      ranged: seats('ranged').map(player)
    },
    healers: seats('healers')
      .map((r) => {
        const healing = Math.round(total(r[0], 'healing'));
        const overheal_percent = Math.round(18 * wobble(s.report_id, r[0], 'oh') * 10) / 10;
        return {
          ...player(r),
          healing,
          overhealing: Math.round((healing * overheal_percent) / 100),
          overheal_percent,
          dispels: Math.round(12 * wobble(s.report_id, r[0], 'dispel')),
          active_percent: Math.min(99, Math.round(92 * wobble(s.report_id, r[0], 'act')))
        };
      })
      .sort((a, b) => b.healing - a.healing),
    tanks: seats('tanks').map((r) => {
      const damage_taken = Math.round(total(r[0], 'damage_taken'));
      const mitigation_percent = Math.round(41 * wobble(s.report_id, r[0], 'mit') * 10) / 10;
      return {
        ...player(r),
        damage_taken,
        mitigated: Math.round((damage_taken * mitigation_percent) / 100),
        mitigation_percent,
        active_percent: 97.5
      };
    }),
    melee: dps('melee'),
    ranged: dps('ranged'),
    consumable_names: CONSUMABLES,
    consumables: ROSTER.map(([name, , role]) => ({
      name,
      role: role.replace(/s$/, ''),
      counts: Object.fromEntries(
        CONSUMABLES.map((c) => [c, Math.floor((wobble(s.report_id, name, c) - 0.85) * 16)]).filter(([, n]) => Number(n) > 0)
      )
    })),
    boss_vs_trash: CONSUMABLES.map((name) => ({
      name,
      boss: Math.round(14 * wobble(s.report_id, name, 'b')),
      trash: Math.round(5 * wobble(s.report_id, name, 't'))
    })),
    interrupts: [
      { name: 'Hopscotch', player_class: 'Rogue', spell_name: 'Kick', count: Math.round(9 * wobble(s.report_id, 'k')) },
      { name: 'Ribbit', player_class: 'Warrior', spell_name: 'Pummel', count: Math.round(6 * wobble(s.report_id, 'p')) },
      { name: 'Reedwhistle', player_class: 'Shaman', spell_name: 'Earth Shock', count: Math.round(4 * wobble(s.report_id, 'e')) }
    ],
    cancelled_casts: seats('healers').map((r) => {
      const total_casts = Math.round(240 * wobble(s.report_id, r[0], 'casts'));
      const cancelled_casts = Math.round(22 * wobble(s.report_id, r[0], 'cc'));
      const cancel_rate = Math.round((cancelled_casts / total_casts) * 1000) / 10;
      return { ...player(r), total_casts, cancelled_casts, cancel_rate, spells: [] };
    }),
    debuff_uptimes: [
      { spell_name: 'Sunder Armor', fight_name: 'All bosses', uptime_percent: 96.4 },
      { spell_name: 'Faerie Fire', fight_name: 'All bosses', uptime_percent: 88.1 },
      { spell_name: 'Curse of the Elements', fight_name: 'All bosses', uptime_percent: 91.7 }
    ],
    totem_uptimes: [
      { spell_name: 'Windfury Totem', fight_name: 'All bosses', uptime_percent: 93.2 },
      { spell_name: 'Mana Spring Totem', fight_name: 'All bosses', uptime_percent: 84.6 }
    ],
    engineering: [
      { name: 'Goblin Sapper Charge', total_casts: 14, total_damage: 30_100, users: 5, min_avg: 1810, median_avg: 2150, max_avg: 2480 }
    ],
    encounters
  };
}

const SUMMARIES = RAIDS.map(summaryOf);
const PAGES = new Map(SUMMARIES.map((s) => [s.report_id, pageOf(s)]));

/** The sample raids' ids, for prerendering their pages. */
export const PREVIEW_RAID_IDS = SUMMARIES.map((s) => s.report_id);

function bosses(): BossHistory[] {
  const out = new Map<number, BossHistory>();
  for (const page of PAGES.values()) {
    const day = String(page.summary.weekday);
    for (const e of page.encounters) {
      const boss = out.get(e.encounter_id) ?? { encounter_id: e.encounter_id, name: e.name, days: {} };
      const totals = (boss.days[day] ??= { kills: 0, duration_ms: 0, damage: 0, healing: 0, players: [] });
      totals.kills += 1;
      totals.duration_ms += e.duration_ms;
      totals.damage += e.damage;
      totals.healing += e.healing;
      for (const p of e.players ?? []) {
        const mine = totals.players!.find((x) => x.name === p.name);
        if (mine) {
          mine.kills += 1;
          mine.damage += p.damage;
          mine.healing += p.healing;
          mine.damage_taken += p.damage_taken;
        } else {
          totals.players!.push({ name: p.name, player_class: p.player_class, role: p.role, kills: 1, damage: p.damage, healing: p.healing, damage_taken: p.damage_taken });
        }
      }
      out.set(e.encounter_id, boss);
    }
  }
  return [...out.values()];
}

/** The weekdays a preview view sees in full; null for every one. */
function fullWeekdays(role: PreviewRole | null): number[] | null {
  return role === 'admin' ? null : role === 'officer' ? [WEDNESDAY] : [];
}

function seesInFull(role: PreviewRole | null, weekday: number | null): boolean {
  const full = fullWeekdays(role);
  return full === null || (weekday !== null && full.includes(weekday));
}

/**
 * Who the preview's pretend sign-in is, for the night Logs opens on: the member and the officer are Wednesday toads
 * (the officer leads Wednesday), the super admin sees every night.
 */
export function previewViewer(role: PreviewRole | null): Pick<Session, 'raid_days' | 'global_officer' | 'super_admin'> {
  return { raid_days: role ? ['wed'] : [], global_officer: role === 'admin', super_admin: role === 'admin' };
}

export function previewLogs(role: () => PreviewRole | null): LogsBackend {
  return {
    async nights(): Promise<Record<string, number>> {
      return { wed: 2, thu: 3, sun: 6 };
    },
    async widgets(): Promise<AnalyzerPage> {
      // One sample page stands in for every night; members do not get the roster's badges, as on the hub.
      const officer = role() === 'officer' || role() === 'admin';
      return { ...analyzerPage, widgets: analyzerPage.widgets.filter((w) => officer || w.id !== 'badges') };
    },
    async overview(): Promise<LogsOverview> {
      const r = role();
      const full = fullWeekdays(r);
      const raids: RaidRow[] = SUMMARIES.map((summary) => {
        const shown = seesInFull(r, summary.weekday);
        return { summary, analysed: true, day: shown && r === 'officer' ? 'wed' : null, full: shown };
      });
      const history = bosses().map((b) => ({
        ...b,
        days: Object.fromEntries(
          Object.entries(b.days).map(([d, t]) => [
            d,
            full === null || full.includes(Number(d)) ? t : { kills: t.kills, duration_ms: t.duration_ms, damage: t.damage, healing: t.healing }
          ])
        )
      }));
      return { generated_at: '2026-10-19 08:00:00', raids, bosses: history, full_weekdays: full };
    },
    async raid(report: string): Promise<RaidView> {
      const page = PAGES.get(report);
      if (!page) throw new ApiError(404, 'This raid has not been analysed yet');
      if (seesInFull(role(), page.summary.weekday)) return { full: true, page };
      const c = page.composition;
      return {
        full: false,
        page: {
          version: page.version,
          summary: page.summary,
          duration_ms: page.duration_ms,
          composition_counts: { tanks: c.tanks.length, healers: c.healers.length, melee: c.melee.length, ranged: c.ranged.length },
          encounters: page.encounters.map(({ players: _, ...e }) => e)
        }
      };
    }
  };
}
