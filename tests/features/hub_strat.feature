# Raid strategy docs (docs/strategy.md): officers keep raid strategy in Google Drive. The hub pins Google Docs per
# classic raid, for every night or for one raid night, and each raid night's Raid page shows the doc for each raid it is
# running.
Feature: HUB STRAT

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-001 When a global officer or super admin pins a Google Doc to a classic raid for every night, the hub shall make it that raid's pinned strategy doc, keep the doc it replaced listed below it, and record it on the audit log
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/naxx-v1" to "naxx"
    And the global officer pins "https://docs.google.com/document/d/naxx-v2" to "naxx" as "Naxx full clear"
    Then the "naxx" strategy is "Naxx full clear" at "https://docs.google.com/document/d/naxx-v2"
    And the "naxx" strategy lists "https://docs.google.com/document/d/naxx-v1" as replaced
    And the audit log records "strategy.pin"
    And every raid from MC to Naxx, and a raid to be decided, can hold a doc

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-002 If a pinned link is not a Google Docs or Drive https link, or names no listed raid or raid night, or a raider or an officer of another night tries to pin a doc through a night, then the hub shall refuse it and change nothing
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/naxx-v1" to "naxx"
    Then pinning "https://example.com/naxx" to "naxx" is refused
    And pinning "http://docs.google.com/document/d/x" to "naxx" is refused
    And pinning "https://docs.google.com/document/d/x" to "kara" is refused
    And pinning "https://docs.google.com/document/d/x" to "naxx" for night "fri" is refused
    And a Wednesday officer cannot pin a doc through Sunday
    And a Wednesday raider cannot pin a doc
    And the "naxx" strategy is "Naxxramas strategy" at "https://docs.google.com/document/d/naxx-v1"

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-003 When a raid night's officer says which raids the night is running, the hub shall show each raid's pinned doc on the night's Raid page to its members
    Given a global officer
    And the global officer pins "https://docs.google.com/document/d/bwl" to "bwl"
    When a Wednesday officer says Wednesday is running "bwl"
    Then a Wednesday raider sees "Blackwing Lair" with "https://docs.google.com/document/d/bwl" on Wednesday's Raid page
    And the audit log records "strategy.night" for Wednesday
    And when the global officer pins "https://docs.google.com/document/d/bwl-v2" to "bwl" the raider sees "https://docs.google.com/document/d/bwl-v2"
    And Sunday's Raid page shows no raid

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-004 If a raider or another raid night's officer tries to say which raids a night is running, then the hub shall refuse it
    Given a global officer
    When a Wednesday officer says Wednesday is running "bwl"
    Then a Sunday officer cannot change Wednesday's raids
    And a Wednesday raider cannot change Wednesday's raids
    And the global officer can say Sunday is running "aq40"
    And the global officer can clear Sunday's raids

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-005 When an officer takes down a pinned doc, the hub shall pin the doc it replaced again
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/mc-v1" to "mc"
    And the global officer pins "https://docs.google.com/document/d/mc-v2" to "mc"
    And the global officer takes down the "mc" pinned doc
    Then the "mc" strategy is "Molten Core strategy" at "https://docs.google.com/document/d/mc-v1"

  @ears_ubiquitous @member @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-006 The Raid page shall show each raid the night is running with its strategy doc, and the officers' Strategy page shall let every officer pin docs for every night or their own night and pick one or more raids for each night they run
    Given the Raid page and the Strategy page
    Then the Raid page shows the night's strategy docs
    And the Strategy page lists the raids, pins docs for every night or one night and picks each night's raids

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-007 When a raid night's officer pins a doc to a raid for their own night, the hub shall add the raid to that night's raids and show that doc on its Raid page in place of the every-night doc, and leave other nights on the every-night doc
    Given a global officer
    And the global officer pins "https://docs.google.com/document/d/aq40-guild" to "aq40"
    And the global officer can say Sunday is running "aq40"
    When a Wednesday officer pins "https://docs.google.com/document/d/aq40-wed" to "aq40" through Wednesday
    Then a Wednesday raider sees "Temple of Ahn'Qiraj" with "https://docs.google.com/document/d/aq40-wed" on Wednesday's Raid page
    And a Sunday raider sees "Temple of Ahn'Qiraj" with "https://docs.google.com/document/d/aq40-guild" on Sunday's Raid page
    And the "aq40" strategy for Wednesday is "https://docs.google.com/document/d/aq40-wed"
    And the audit log records "strategy.pin" for Wednesday
    And when the Wednesday officer takes down the "aq40" Wednesday doc a Wednesday raider sees "https://docs.google.com/document/d/aq40-guild"

  @ears_state_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-008 While a raid night is running more than one raid, its Raid page shall show each raid's doc, in the order the night runs them
    Given a global officer
    And the global officer pins "https://docs.google.com/document/d/zg" to "zg"
    And the global officer pins "https://docs.google.com/document/d/aq20" to "aq20"
    When a Wednesday officer says Wednesday is running "aq20" then "zg" then "mc"
    Then Wednesday's Raid page shows "aq20" at "https://docs.google.com/document/d/aq20", "zg" at "https://docs.google.com/document/d/zg" and "mc" with no doc

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-009 If a raid night's officer takes down another night's doc, then the hub shall refuse it; a night's officer may pin and take down every-night docs
    Given a global officer
    When the global officer pins "https://docs.google.com/document/d/naxx-sun" to "naxx" for night "sun"
    And a Wednesday officer pins "https://docs.google.com/document/d/naxx-all" to "naxx" for every night through Wednesday
    Then the Wednesday officer cannot take down Sunday's "naxx" doc
    And the Wednesday officer can take down the every-night "naxx" doc
