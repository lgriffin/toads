/**
 * Sample Toads badges for the static preview, awarded exactly as wcl_app.badges awards them (guides/badges.md in
 * lgriffin/warcraftlogs_project): the default rules and thresholds, a counted value per badge, the tier it reaches.
 */

import type { Badge, BadgeHolder, MyBadges, PlayerBadges, Quality } from '../badges';

interface Rule {
  id: string;
  name: string;
  description: string;
  icon: string;
  glyph: string;
  unit: string;
  thresholds: number[];
}

const QUALITIES: Quality[] = ['uncommon', 'rare', 'epic', 'legendary'];

const RULES: Rule[] = [
  { id: 'attendance', name: 'Loyal Toad', description: 'Raids attended', icon: 'attendance', glyph: '🐸', unit: 'raids', thresholds: [5, 15, 40, 100] },
  { id: 'well_stocked', name: 'Well Stocked', description: 'Consumables used', icon: 'consumables', glyph: '🎒', unit: 'consumables', thresholds: [50, 250, 750, 2000] },
  { id: 'mana_potions', name: 'Mana Guzzler', description: 'Mana potions', icon: 'mana_potion', glyph: '🧪', unit: 'potions', thresholds: [10, 50, 150, 400] },
  { id: 'healing_potions', name: 'Survivor', description: 'Healing potions and healthstones', icon: 'healing_potion', glyph: '💗', unit: 'potions', thresholds: [10, 40, 100, 250] },
  { id: 'combat_potions', name: 'Liquid Courage', description: 'Destruction, Haste and other combat potions', icon: 'combat_potion', glyph: '🔥', unit: 'potions', thresholds: [10, 50, 150, 400] },
  { id: 'runes', name: 'Rune Eater', description: 'Dark and Demonic Runes', icon: 'rune', glyph: '🔮', unit: 'runes', thresholds: [10, 40, 100, 250] },
  { id: 'drums', name: 'Drummer', description: 'Drums of Battle', icon: 'drums', glyph: '🥁', unit: 'drums', thresholds: [10, 50, 150, 400] },
  { id: 'explosives', name: 'Sapper', description: 'Sapper charges, grenades and bombs', icon: 'explosive', glyph: '💣', unit: 'explosives', thresholds: [10, 50, 150, 400] },
  { id: 'weapon_enhancements', name: 'Sharpened', description: 'Weapon oils and stones', icon: 'weapon_enhancement', glyph: '✨', unit: 'applications', thresholds: [5, 20, 50, 120] },
  { id: 'scrolls', name: 'Scholar', description: 'Scrolls of Agility and Strength', icon: 'scroll', glyph: '📜', unit: 'scrolls', thresholds: [5, 20, 50, 120] },
  { id: 'flasked', name: 'Flask Bearer', description: 'Raids with a flask or an elixir pair', icon: 'flask', glyph: '⚗️', unit: 'raids', thresholds: [5, 15, 40, 100] }
];

const quality = (tier: number): Quality => (tier >= 1 && tier <= QUALITIES.length ? QUALITIES[tier - 1] : '');
const title = (q: Quality) => q.charAt(0).toUpperCase() + q.slice(1);

function award(rule: Rule, value: number): Badge {
  const tier = rule.thresholds.filter((at) => value >= at).length;
  const nextAt = tier < rule.thresholds.length ? rule.thresholds[tier] : null;
  const floor = tier ? rule.thresholds[tier - 1] : 0;
  const unit = value === 1 ? rule.unit.replace(/s$/, '') : rule.unit;
  return {
    id: rule.id,
    name: rule.name,
    description: rule.description,
    icon: rule.icon,
    glyph: rule.glyph,
    tier,
    quality: quality(tier),
    tier_name: title(quality(tier)),
    value,
    display: `${value.toLocaleString('en-GB')} ${unit}`,
    stacks: Math.floor(value / rule.thresholds[0]),
    next_at: nextAt,
    next_tier: nextAt === null ? '' : title(quality(tier + 1)),
    progress: nextAt === null ? 1 : Math.round(((value - floor) / (nextAt - floor)) * 1000) / 1000
  };
}

/** Counts in catalogue order: raids, all consumables, mana, healing, combat, runes, drums, explosives, oils, scrolls, raids prepared. */
function player(name: string, playerClass: string, counts: number[]): PlayerBadges {
  const badges = RULES.map((rule, i) => award(rule, counts[i] ?? 0));
  return { name, player_class: playerClass, score: badges.reduce((n, b) => n + b.tier, 0), badges };
}

/** The last raid's roster, most tiers first, as wcl_app.home's `badges` widget ranks it. */
export const roster: PlayerBadges[] = [
  player('Hopscotch', 'Rogue', [104, 812, 0, 118, 212, 64, 0, 172, 58, 44, 101]),
  player('Lilypadd', 'Shaman', [96, 690, 318, 41, 0, 122, 0, 0, 36, 0, 90]),
  player('Bogwalker', 'Warrior', [88, 540, 0, 96, 160, 0, 0, 48, 52, 38, 61]),
  player('Mossback', 'Priest', [71, 402, 246, 27, 0, 88, 0, 0, 22, 0, 44]),
  player('Wartsworth', 'Mage', [52, 318, 180, 22, 64, 30, 0, 0, 18, 0, 12]),
  player('Tadpole', 'Hunter', [23, 144, 0, 16, 42, 0, 12, 18, 9, 6, 17]),
  player('Croakwell', 'Priest', [9, 61, 38, 4, 0, 11, 0, 0, 3, 0, 2])
].sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

export const badgeHolders: BadgeHolder[] = roster.map((p) => ({
  name: p.name,
  player_class: p.player_class,
  badges: p.badges.filter((b) => b.tier > 0),
  link: { kind: 'character', params: { name: p.name } }
}));

/** GET /api/me/badges for the preview visitor, Hopscotch. */
export const previewBadges: MyBadges = {
  generated_at: '2026-09-25 08:00:00',
  entry: roster.find((p) => p.name === 'Hopscotch') ?? null,
  matched_by: 'claim',
  looked_for: ['Hopscotch', 'Lilypadd']
};
