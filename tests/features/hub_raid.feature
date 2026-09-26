# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB RAID

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-RAID-001 Every analysed raid shall show role breakdown, consumable coverage split by boss and trash, interrupts and cancelled casts

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-RAID-002 The raid filters shall match the desktop app's: zone, raid day, size, lookback

  @ears_optional @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-RAID-003 Where a raid group is defined, attendance and role coverage shall be computed against that group
