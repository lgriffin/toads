/**
 * The customisable hub home. Widget ids are a contract with the API's home service
 * (services/api/src/toads_api/home/service.py): add a widget there and here together. Analyzer widget ids are the
 * analyzer's own (wcl_app.home in lgriffin/warcraftlogs_project). The API decides which widgets a
 * member may place (officer widgets need officer powers); this file only mirrors the catalogue so the static preview
 * and the customiser can work without a round trip.
 */

export type WidgetId =
  | 'next_raid'
  | 'officer_desk'
  | 'guild_snapshot'
  | 'last_raid'
  | 'my_performance'
  | 'raid_totals'
  | 'recent_raids'
  | 'raid_activity'
  | 'healing_weekly'
  | 'top_damage'
  | 'top_healing'
  | 'attendance'
  | 'badges'
  | 'posts'
  | 'highlights'
  | 'boss_kills'
  | 'class_mix'
  | 'interrupts'
  | 'consumables'
  | 'healers_weekly'
  | 'progression'
  | 'recruiting';

/** "hub": drawn from the hub's own data. "analyzer": a widget of the analyzer's shared home page ($lib/home-payload). */
export type WidgetSource = 'hub' | 'analyzer';

/** One widget as GET /api/me/home describes it. */
export interface HomeWidget {
  id: WidgetId;
  title: string;
  description: string;
  officer_only: boolean;
  source: WidgetSource;
  shown: boolean;
}

/** GET/PUT/DELETE /api/me/home: every widget the member may place, in display order. */
export interface HomeLayout {
  widgets: HomeWidget[];
  /** False while the member is on the default layout. */
  customised: boolean;
}

interface CatalogueEntry extends Omit<HomeWidget, 'shown'> {
  defaultShown: boolean;
  /** Spans the whole row on wide screens (the analyzer's `size: "full"`). */
  wide?: boolean;
}

function hub(id: WidgetId, title: string, description: string, extra: Partial<CatalogueEntry> = {}): CatalogueEntry {
  return { id, title, description, officer_only: false, source: 'hub', defaultShown: true, ...extra };
}

function analyzer(id: WidgetId, title: string, description: string, extra: Partial<CatalogueEntry> = {}): CatalogueEntry {
  return { id, title, description, officer_only: false, source: 'analyzer', defaultShown: true, ...extra };
}

/**
 * In default display order, as in the API. Analyzer ids, titles and sizes follow the analyzer's catalogue
 * (guides/home_widgets.md in lgriffin/warcraftlogs_project); its quick actions and tracked players have no hub page.
 */
export const CATALOGUE: readonly CatalogueEntry[] = [
  hub('next_raid', 'Next raid', 'When the next raid starts and how many have signed up in Discord.'),
  hub('officer_desk', 'Raid leader desk', 'Applications, posts, highlights and spotlights waiting on officers.', {
    officer_only: true
  }),
  analyzer('guild_snapshot', 'Guild at a glance', 'Raids stored, active raiders, raids this month, last raid.', {
    wide: true
  }),
  analyzer('last_raid', 'Last raid', 'Date, duration, bosses killed, raid size, total damage and healing.', { wide: true }),
  hub('my_performance', 'Your performance', "Your main character's last raid against the guild median."),
  hub('raid_totals', 'Raid totals', 'Consumes, buffs and deaths per raid from the CBA and RPB sheets.', { wide: true }),
  analyzer('recent_raids', 'Recent raids', 'The newest guild raids.'),
  analyzer('raid_activity', 'Raid activity', 'Raids per week over the last eight weeks.'),
  analyzer(
    'healing_weekly',
    'Weekly healing',
    'Healing per raid each week, measured against its four-week average.',
    { wide: true }
  ),
  analyzer(
    'healers_weekly',
    'Healers week on week',
    "Average healing per character each week, with each healer's healing per raid.",
    { wide: true }
  ),
  analyzer('top_damage', 'Top damage', 'The top five damage dealers in the last raid.'),
  analyzer('top_healing', 'Top healing', 'The top five healers in the last raid, with overheal.'),
  analyzer('attendance', 'Attendance', 'Who attended most of the last ten raids.'),
  // The whole roster's badges are for raid leaders; each member sees their own on /me.
  analyzer('badges', 'Toads badges', "Badges earned by the last raid's roster, most tiers first.", {
    officer_only: true
  }),
  hub('posts', 'Guild posts', 'News and posts from officers and Discord.'),
  hub('highlights', 'Recent highlights', 'The newest highlight reels.'),
  analyzer('boss_kills', 'Boss kills', 'Bosses killed in the last raid, in kill order.', { defaultShown: false }),
  analyzer('class_mix', 'Class mix', 'Players per class in the last raid.', { defaultShown: false }),
  analyzer('interrupts', 'Interrupt casts', 'The most interrupt abilities cast in the last raid.', {
    defaultShown: false
  }),
  analyzer('consumables', 'Consumables', 'The top five consumable users in the last raid.', { defaultShown: false }),
  hub('progression', 'Progression', 'Bosses killed in each raid zone.', { defaultShown: false }),
  hub('recruiting', 'Recruiting', 'The classes and specs the guild is looking for.', { defaultShown: false })
];

const WIDE = new Set(CATALOGUE.filter((w) => w.wide).map((w) => w.id));

export function isWide(id: WidgetId): boolean {
  return WIDE.has(id);
}

const ANALYZER = new Set(CATALOGUE.filter((w) => w.source === 'analyzer').map((w) => w.id));

/** Drawn from the analyzer's page (GET /api/home/analyzer) rather than the hub's own data. */
export function isAnalyzer(id: WidgetId): boolean {
  return ANALYZER.has(id);
}

export function catalogueTitle(id: WidgetId): string {
  return CATALOGUE.find((w) => w.id === id)?.title ?? id;
}

/** The layout a member who never customised sees; the API answers the same. */
export function defaultLayout(officer: boolean): HomeLayout {
  return {
    widgets: CATALOGUE.filter((w) => officer || !w.officer_only).map((w) => ({
      id: w.id,
      title: w.title,
      description: w.description,
      officer_only: w.officer_only,
      source: w.source,
      shown: w.defaultShown
    })),
    customised: false
  };
}

export function shownIds(layout: HomeLayout): WidgetId[] {
  return layout.widgets.filter((w) => w.shown).map((w) => w.id);
}

/** Moves a widget one place up (-1) or down (+1); unchanged at either end. */
export function move(widgets: readonly HomeWidget[], id: WidgetId, by: -1 | 1): HomeWidget[] {
  const out = [...widgets];
  const i = out.findIndex((w) => w.id === id);
  const j = i + by;
  if (i < 0 || j < 0 || j >= out.length) return out;
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

export function toggle(widgets: readonly HomeWidget[], id: WidgetId): HomeWidget[] {
  return widgets.map((w) => (w.id === id ? { ...w, shown: !w.shown } : w));
}

/**
 * What saving `widgets` leaves the member with, as the API would answer: the shown widgets in order, then the hidden
 * ones. Used by the preview, which has no API.
 */
export function saved(widgets: readonly HomeWidget[]): HomeLayout {
  return { widgets: [...widgets.filter((w) => w.shown), ...widgets.filter((w) => !w.shown)], customised: true };
}
