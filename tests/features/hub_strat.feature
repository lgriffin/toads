# Raid strategy docs (docs/strategy.md): officers keep raid strategy in Google Drive. The hub pins one Google Doc per
# classic raid as its authoritative strategy, and each raid night's Raid page shows the doc for the raid it is running.
Feature: HUB STRAT

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-001 When a global officer or super admin pins a Google Doc to a classic raid, the hub shall make it that raid's one pinned strategy doc, keep the doc it replaced listed below it, and record it on the audit log
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/naxx-v1" to "naxx"
    And the global officer pins "https://docs.google.com/document/d/naxx-v2" to "naxx" as "Naxx full clear"
    Then the "naxx" strategy is "Naxx full clear" at "https://docs.google.com/document/d/naxx-v2"
    And the "naxx" strategy lists "https://docs.google.com/document/d/naxx-v1" as replaced
    And the audit log records "strategy.pin"
    And every raid from MC to Naxx, and a raid to be decided, can hold a doc

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-002 If a pinned link is not a Google Docs or Drive https link, or names no listed raid, or a raider or an officer of another night tries to pin a doc through a night, then the hub shall refuse it and change nothing
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/naxx-v1" to "naxx"
    Then pinning "https://example.com/naxx" to "naxx" is refused
    And pinning "http://docs.google.com/document/d/x" to "naxx" is refused
    And pinning "https://docs.google.com/document/d/x" to "kara" is refused
    And a Wednesday officer cannot pin a doc through Sunday
    And a Wednesday raider cannot pin a doc
    And the "naxx" strategy is "Naxxramas strategy" at "https://docs.google.com/document/d/naxx-v1"

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-003 When a raid night's officer says which raid the night is running, the hub shall show that raid's pinned doc on the night's Raid page to its members
    Given a global officer
    And the global officer pins "https://docs.google.com/document/d/bwl" to "bwl"
    When a Wednesday officer says Wednesday is running "bwl"
    Then a Wednesday raider sees "Blackwing Lair" with "https://docs.google.com/document/d/bwl" on Wednesday's Raid page
    And the audit log records "strategy.night" for Wednesday
    And when the global officer pins "https://docs.google.com/document/d/bwl-v2" to "bwl" the raider sees "https://docs.google.com/document/d/bwl-v2"
    And Sunday's Raid page shows no raid

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-004 If a raider or another raid night's officer tries to say which raid a night is running, then the hub shall refuse it
    Given a global officer
    When a Wednesday officer says Wednesday is running "bwl"
    Then a Sunday officer cannot change Wednesday's raid
    And a Wednesday raider cannot change Wednesday's raid
    And the global officer can say Sunday is running "aq40"
    And the global officer can clear Sunday's raid

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-005 When a global officer takes down a raid's pinned doc, the hub shall pin the doc it replaced again
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/mc-v1" to "mc"
    And the global officer pins "https://docs.google.com/document/d/mc-v2" to "mc"
    And the global officer takes down the "mc" pinned doc
    Then the "mc" strategy is "Molten Core strategy" at "https://docs.google.com/document/d/mc-v1"

  @ears_ubiquitous @member @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-006 The Raid page shall show the night's raid and its pinned strategy doc, and the officers' Strategy page shall let every officer pin docs and each night's officers pick their night's raid
    Given the Raid page and the Strategy page
    Then the Raid page shows the night's strategy doc
    And the Strategy page lists the raids, pins docs for every officer and picks each night's raid

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-007 When a raid night's officer pins or takes down a raid's doc through their night, the hub shall change that raid's pinned doc for every night running it and record the night on the audit log
    Given a global officer
    And the global officer pins "https://docs.google.com/document/d/aq40-v1" to "aq40"
    When a Wednesday officer pins "https://docs.google.com/document/d/aq40-v2" to "aq40" through Wednesday
    And the global officer can say Sunday is running "aq40"
    Then a Sunday raider sees "Temple of Ahn'Qiraj" with "https://docs.google.com/document/d/aq40-v2" on Sunday's Raid page
    And the audit log records "strategy.pin" for Wednesday
    And when the Wednesday officer takes down the "aq40" pinned doc through Wednesday a Sunday raider sees "https://docs.google.com/document/d/aq40-v1"
