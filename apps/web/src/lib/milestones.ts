/**
 * The milestone and achievement toads. Generated with the artwork: `file` is the toad under static/logos/ (add
 * `-badge` for the badge with its name). Awarding one to a member is the hub's job; this is the catalogue it draws on.
 */
export type MilestoneCategory =
  | 'attendance'
  | 'recognition'
  | 'history'
  | 'levelling'
  | 'collection'
  | 'professions'
  | 'pvp'
  | 'raiding'
  | 'pond';

export interface Milestone {
  id: string;
  name: string;
  blurb: string;
  category: MilestoneCategory;
  /** The badge's own colour, for the plate and the disc. */
  colour: string;
  file: string;
}

export const MILESTONES: readonly Milestone[] = [
  { id: 'raids-10', name: '10 Raids', blurb: 'Turned up for 10 raids.', category: 'attendance', colour: '#b87333', file: 'milestones/raids-10' },
  { id: 'raids-20', name: '20 Raids', blurb: 'Turned up for 20 raids.', category: 'attendance', colour: '#c0c8d0', file: 'milestones/raids-20' },
  { id: 'raids-50', name: '50 Raids', blurb: 'Turned up for 50 raids.', category: 'attendance', colour: '#f2c14e', file: 'milestones/raids-50' },
  { id: 'raids-100', name: '100 Raids', blurb: 'Turned up for 100 raids. A pillar of the pond.', category: 'attendance', colour: '#5fe6d6', file: 'milestones/raids-100' },
  { id: 'raider-of-the-month', name: 'Raider of the Month', blurb: 'Named the guild’s raider of the month.', category: 'recognition', colour: '#f2c14e', file: 'milestones/raider-of-the-month' },
  { id: 'veteran-fresh', name: 'Classic Fresh', blurb: 'Raided with us in Classic Fresh.', category: 'history', colour: '#c9a25a', file: 'milestones/veteran-fresh' },
  { id: 'veteran-tbc', name: 'TBC Veteran', blurb: 'Raided with us in The Burning Crusade.', category: 'history', colour: '#46b84a', file: 'milestones/veteran-tbc' },
  { id: 'level-60', name: 'Level 60', blurb: 'Hit the level cap in Classic.', category: 'levelling', colour: '#a335ee', file: 'badges/level-60' },
  { id: 'alt-60', name: 'Sixty Alt', blurb: 'Took a second character to 60. Huge.', category: 'levelling', colour: '#c15bff', file: 'badges/alt-60' },
  { id: 'level-70', name: 'Level 70', blurb: 'Hit the level cap in The Burning Crusade.', category: 'levelling', colour: '#46b84a', file: 'badges/level-70' },
  { id: 'epic-mount', name: 'Epic Mount', blurb: 'Bought the 100% mount.', category: 'collection', colour: '#a335ee', file: 'badges/epic-mount' },
  { id: 'flying-mount', name: 'Taking Flight', blurb: 'Earned a flying mount.', category: 'collection', colour: '#69CCF0', file: 'badges/flying-mount' },
  { id: 'dungeon-set', name: 'Dungeon Set', blurb: 'Pieced together a dungeon set.', category: 'collection', colour: '#0070dd', file: 'badges/dungeon-set' },
  { id: 'full-tier', name: 'Full Tier', blurb: 'Completed a raid tier set.', category: 'collection', colour: '#a335ee', file: 'badges/full-tier' },
  { id: 'legendary', name: 'Legendary', blurb: 'Got a legendary drop.', category: 'collection', colour: '#ff8000', file: 'badges/legendary' },
  { id: 'master-crafter', name: 'Master Crafter', blurb: 'Maxed a crafting profession.', category: 'professions', colour: '#9aa4ad', file: 'badges/master-crafter' },
  { id: 'master-angler', name: 'Master Angler', blurb: 'Fished to 300.', category: 'professions', colour: '#2f9bd6', file: 'badges/master-angler' },
  { id: 'chef', name: 'Chef', blurb: 'Cooked to 300.', category: 'professions', colour: '#f0f0f6', file: 'badges/chef' },
  { id: 'thousand-gold', name: '1,000 Gold', blurb: 'Saved a thousand gold.', category: 'collection', colour: '#f2c14e', file: 'badges/thousand-gold' },
  { id: 'pvp-rank-10', name: 'Rank 10', blurb: 'Climbed to honor rank 10.', category: 'pvp', colour: '#c0392b', file: 'badges/pvp-rank-10' },
  { id: 'pvp-rank-14', name: 'Rank 14', blurb: 'Reached the top of the honor ladder.', category: 'pvp', colour: '#8a1f1f', file: 'badges/pvp-rank-14' },
  { id: 'flag-runner', name: 'Flag Runner', blurb: 'Carried the flag home.', category: 'pvp', colour: '#b8342e', file: 'badges/flag-runner' },
  { id: 'tarren-mill', name: 'Tarren Mill', blurb: 'Fought the Hillsbrad grudge match.', category: 'pvp', colour: '#7a2418', file: 'badges/tarren-mill' },
  { id: 'scarab-lord', name: 'Scarab Lord', blurb: 'Rang the gong and opened the gates.', category: 'raiding', colour: '#d9b45a', file: 'badges/scarab-lord' },
  { id: 'dragonslayer', name: 'Dragonslayer', blurb: 'Brought down the black dragon in her lair.', category: 'raiding', colour: '#9b2d20', file: 'badges/dragonslayer' },
  { id: 'firelord', name: 'Firelord', blurb: 'Put out the fire in Molten Core.', category: 'raiding', colour: '#ff5a14', file: 'badges/firelord' },
  { id: 'blackwing-down', name: 'Blackwing Down', blurb: 'Cleared Blackwing Lair.', category: 'raiding', colour: '#5a1a1a', file: 'badges/blackwing-down' },
  { id: 'cthun-down', name: 'C’Thun Down', blurb: 'Looked the Old God in the eye and won.', category: 'raiding', colour: '#6a8f2a', file: 'badges/cthun-down' },
  { id: 'lich-slayer', name: 'Lich Slayer', blurb: 'Broke the Lich King’s lieutenant in Naxxramas.', category: 'raiding', colour: '#9fd8f0', file: 'badges/lich-slayer' },
  { id: 'serpent-slayer', name: 'Serpentshrine', blurb: 'Cleared Serpentshrine Cavern.', category: 'raiding', colour: '#1f9aa0', file: 'badges/serpent-slayer' },
  { id: 'illidan-down', name: 'Illidan Down', blurb: 'Was not prepared. Was prepared.', category: 'raiding', colour: '#3a8f2a', file: 'badges/illidan-down' },
  { id: 'attuned', name: 'Attuned', blurb: 'Earned the key to the tower.', category: 'collection', colour: '#c58f45', file: 'badges/attuned' },
  { id: 'wipe-veteran', name: 'Wipe Veteran', blurb: 'Wiped, ran back and tried again.', category: 'raiding', colour: '#8a8fa0', file: 'badges/wipe-veteran' },
  { id: 'always-flasked', name: 'Always Flasked', blurb: 'Never raided without a flask.', category: 'raiding', colour: '#3fe08a', file: 'badges/always-flasked' },
  { id: 'generous', name: 'Generous', blurb: 'Gave to the guild bank.', category: 'pond', colour: '#e0708a', file: 'badges/generous' },
  { id: 'pond-builder', name: 'Pond Builder', blurb: 'Brought a friend to the pond.', category: 'pond', colour: '#5fc08a', file: 'badges/pond-builder' },
  { id: 'voice-regular', name: 'Voice Regular', blurb: 'Always on voice chat.', category: 'pond', colour: '#6a7bff', file: 'badges/voice-regular' },
  { id: 'hardcore', name: 'Hardcore', blurb: 'Survived hardcore.', category: 'levelling', colour: '#3a3f4a', file: 'badges/hardcore' },
  { id: 'exalted', name: 'Exalted', blurb: 'Exalted with a faction.', category: 'levelling', colour: '#8e5cd9', file: 'badges/exalted' }
];
