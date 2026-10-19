# Members' awards (docs/awards.md): the milestone, achievement and title toads officers give members, and the Discord
# username the hub keeps so it can recognise a member exactly whatever their server nickname.
Feature: HUB AWARD

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-AWARD-001 The hub shall store each member's Discord username, refreshed at every sign-in, and report it in the member's session alongside their server nickname
    Given a raider who goes by the nickname "Lord Ribbit"
    When they sign in
    Then their session reports their Discord username and the nickname "Lord Ribbit"
    And their member row holds their Discord username

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-AWARD-002 When a global officer gives a member an award from the catalogue, the hub shall store it, show it to the member and among the guild's awards, and record it on the audit log
    Given a raider who goes by the nickname "Hopscotch"
    And a global officer
    When the global officer gives the raider the "level-60" award
    Then the raider sees "Level 60" among their awards
    And the guild's awards include "Level 60" for "Hopscotch"
    And the audit log records "award.give"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-AWARD-003 If a raid-day officer or a raider tries to give an award, then the hub shall refuse it and store nothing
    Given a raider who goes by the nickname "Hopscotch"
    And a Wednesday officer
    When the Wednesday officer tries to give the raider the "level-60" award
    Then the request is refused as forbidden
    And no award is stored

  @ears_state_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-AWARD-004 While an award is monthly, the hub shall require the month it is for and let a member hold it once per month; every other award a member shall hold once
    Given a raider who goes by the nickname "Hopscotch"
    And a global officer
    When the global officer gives the raider Raider of the Month for "2026-09" and for "2026-10"
    Then the raider holds Raider of the Month twice
    And giving it again for "2026-10" is refused as a duplicate
    And giving it with no month is refused

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-AWARD-005 When a global officer takes an award back, the hub shall remove it from the member and record that on the audit log
    Given a raider who goes by the nickname "Hopscotch"
    And a global officer
    When the global officer gives the raider the "chef" award
    And the global officer takes it back
    Then the raider holds no awards
    And the audit log records "award.take_back"
