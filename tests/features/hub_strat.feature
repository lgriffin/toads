# Raid strategy docs (docs/strategy.md): officers keep raid strategy in Google Drive. Officers add Google Docs to each
# classic raid, then each raid night pins the docs its raiders see on the night's Raid page.
Feature: HUB STRAT

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-001 When an officer adds a Google Doc to a classic raid, the hub shall list it under that raid, newest first, keep it from raiders until a night pins it, and record it on the audit log
    Given a global officer
    When the global officer adds "https://docs.google.com/document/d/naxx-v1" to "naxx"
    And the global officer adds "https://docs.google.com/document/d/naxx-v2" to "naxx" as "Naxx full clear"
    Then the "naxx" docs are "Naxx full clear" then "Naxxramas strategy"
    And the audit log records "strategy.add"
    And Wednesday's Raid page shows no docs
    And every raid from MC to Naxx, and a raid to be decided, can hold a doc

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-002 If an added link is not a Google Docs or Drive https link, or names no listed raid, or a raider or an officer of another night tries to add a doc through a night, then the hub shall refuse it and change nothing
    Given a global officer
    When the global officer adds "https://docs.google.com/document/d/naxx-v1" to "naxx"
    Then adding "https://example.com/naxx" to "naxx" is refused
    And adding "http://docs.google.com/document/d/x" to "naxx" is refused
    And adding "https://docs.google.com/document/d/x" to "kara" is refused
    And a Wednesday officer cannot add a doc through Sunday
    And a Wednesday raider cannot add a doc
    And the "naxx" docs are "Naxxramas strategy"

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-003 When a raid night's officer pins docs for the night's raiders, the hub shall show them on the night's Raid page to its members, in the order pinned, and record it on the audit log
    Given a global officer
    And the global officer adds "https://docs.google.com/document/d/bwl" to "bwl"
    And the global officer adds "https://docs.google.com/document/d/zg" to "zg"
    When a Wednesday officer pins "https://docs.google.com/document/d/zg" then "https://docs.google.com/document/d/bwl" for Wednesday
    Then a Wednesday raider sees "zg" at "https://docs.google.com/document/d/zg" then "bwl" at "https://docs.google.com/document/d/bwl"
    And the audit log records "strategy.night" for Wednesday
    And the "bwl" doc lists Wednesday as pinning it
    And Sunday's Raid page shows no docs

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-004 If a raider or another raid night's officer tries to pin a night's docs, or a pin names a doc not listed, then the hub shall refuse it
    Given a global officer
    And the global officer adds "https://docs.google.com/document/d/aq40" to "aq40"
    When a Wednesday officer pins "https://docs.google.com/document/d/aq40" for Wednesday
    Then a Sunday officer cannot pin Wednesday's docs
    And a Wednesday raider cannot pin Wednesday's docs
    And pinning a doc that is not listed for Wednesday is refused
    And the global officer can pin "https://docs.google.com/document/d/aq40" for Sunday
    And the global officer can clear Sunday's docs

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-STRAT-005 When an officer takes a doc down, the hub shall remove it from the raid and from every night that pins it
    Given a global officer
    And the global officer adds "https://docs.google.com/document/d/mc" to "mc"
    When a Wednesday officer pins "https://docs.google.com/document/d/mc" for Wednesday
    And the global officer takes down "https://docs.google.com/document/d/mc"
    Then Wednesday's Raid page shows no docs
    And the "mc" docs are empty

  @ears_ubiquitous @member @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-006 The officers' Strategy page shall let every officer add docs to each raid, and the Raid page shall show the night's pinned docs and let its officers pin them from the raids' docs
    Given the Raid page and the Strategy page
    Then the Raid page shows the night's pinned docs and lets its officers pin them
    And the Strategy page adds docs to each raid and pins each night's docs

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-007 When a raid night's officer adds a doc through their night, the hub shall list it under the raid for every night's officers to pin, and record the night on the audit log
    Given a global officer
    When a Wednesday officer adds "https://docs.google.com/document/d/aq20-wed" to "aq20" through Wednesday
    Then the "aq20" docs are "Ruins of Ahn'Qiraj strategy"
    And the audit log records "strategy.add" for Wednesday
    And a Sunday officer can pin "https://docs.google.com/document/d/aq20-wed" for Sunday

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-STRAT-008 If a raid night's officer tries to take down a doc another night pins, then the hub shall refuse it; they may take down a doc no other night pins
    Given a global officer
    And the global officer adds "https://docs.google.com/document/d/naxx-sun" to "naxx"
    And the global officer can pin "https://docs.google.com/document/d/naxx-sun" for Sunday
    When a Wednesday officer adds "https://docs.google.com/document/d/naxx-wed" to "naxx" through Wednesday
    And a Wednesday officer pins "https://docs.google.com/document/d/naxx-wed" for Wednesday
    Then the Wednesday officer cannot take down "https://docs.google.com/document/d/naxx-sun"
    And the Wednesday officer can take down "https://docs.google.com/document/d/naxx-wed"
