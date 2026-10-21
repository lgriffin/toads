# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
# The Logs page (docs/logs.md): the analyzer's raid list, raid analysis and boss history, by weekday.
Feature: HUB RAID

  @ears_ubiquitous @raid_leader @phase_2_6
  Scenario: REQ-HUB-RAID-001 Every analysed raid shall show role breakdown, consumable coverage split by boss and trash, interrupts and cancelled casts
    Given the worker has published a Wednesday raid "wedSSC" and a Thursday raid "thuTK"
    And a Wednesday officer
    When the Wednesday officer opens "wedSSC"
    Then the raid shows its role breakdown, consumables split by boss and trash, interrupts and cancelled casts

  @ears_ubiquitous @member @phase_2_6
  Scenario: REQ-HUB-RAID-002 The Logs list shall give every raid its weekday, so the page filters raids by any mix of weekdays, zone and title as the desktop raid list does
    Given the worker has published a Wednesday raid "wedSSC" and a Thursday raid "thuTK"
    And a Wednesday raider
    When the raider lists the raids
    Then "wedSSC" is listed on weekday 2 and "thuTK" on weekday 3

  @ears_optional @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-RAID-003 Where a raid group is defined, attendance and role coverage shall be computed against that group

  @ears_state_driven @member @phase_2_7
  Scenario: REQ-HUB-RAID-004 While a member is not an officer of a raid's weekday, the hub shall show them that raid's boss totals and makeup but no raider's own numbers; a global officer shall see every raid in full
    Given the worker has published a Wednesday raid "wedSSC" and a Thursday raid "thuTK"
    And a Wednesday raider
    And a Wednesday officer
    And a global officer
    Then the raider sees "wedSSC" without anyone's numbers
    And the Wednesday officer sees "thuTK" without anyone's numbers
    And the global officer sees "thuTK" in full

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-RAID-005 The hub shall keep the analyzer's raid widgets for each raid night, built from that night's raids only, so Logs opens on the night of the member's Toad badge
    Given the worker has published the guild's raid widgets and each raid night's own
    And a Wednesday raider
    When the raider opens the Wednesday widgets on Logs
    Then the raider sees Wednesday's last raid and not the guild-wide one

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-RAID-006 When a member opens a raid from the analyzer's widgets on Logs, the hub shall open that raid's breakdown under Logs rather than its Warcraft Logs report, under the night a night officer reads in full
    Given the analyzer's widgets link a raid by its report id
    Then the link opens the raid's page under Logs
    And a night officer's link carries their raid night

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-RAID-007 If the hub refuses one raid's analysis, the worker shall still send every other raid's analysis, then fail the run naming the refused raid
    Given the worker holds the analyses of "wedSSC" and "thuTK"
    And the hub refuses the analysis of "wedSSC"
    When the worker publishes the Logs page
    Then the run fails naming "wedSSC"
    And a Wednesday raider opening "thuTK" sees its analysis
