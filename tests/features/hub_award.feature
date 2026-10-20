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

  # Role badges (docs/role-badges.md): badge toads members earn from the Discord roles they hold, such as the
  # Wednesday Toad, the Sunday Toad, Tank and Healer. A super admin ties each badge to a server role on the admin page.

  @ears_event_driven @maintainer @phase_2_7
  Scenario: REQ-HUB-AWARD-006 When a super admin ties a badge to a Discord server role, the hub shall show that badge to every member holding the role and record it on the audit log
    Given a Discord role named "Wednesday Toad"
    And a raider who holds the "Wednesday Toad" role
    And a super admin
    When the super admin ties the "wednesday-toad" badge to the "Wednesday Toad" role
    Then the raider sees the "Wednesday Toad" badge among their role badges
    And the audit log records "role_badge.add"

  @ears_unwanted_behavior @maintainer @phase_2_7
  Scenario: REQ-HUB-AWARD-007 If a global officer tries to tie a badge to a Discord role, then the hub shall refuse it and store nothing
    Given a Discord role named "Healers"
    And a global officer
    When the global officer tries to tie the "healer" badge to the "Healers" role
    Then the request is refused as forbidden
    And no role badge is stored

  @ears_unwanted_behavior @maintainer @phase_2_7
  Scenario: REQ-HUB-AWARD-008 If a super admin names a badge outside the catalogue or a role that is not in the Discord server, then the hub shall refuse it and store nothing
    Given a Discord role named "Tanks"
    And a super admin
    When the super admin ties the "not-a-badge" badge to the "Tanks" role
    Then the request is refused as invalid
    When the super admin ties the "tank" badge to a role the server does not have
    Then the request is refused as invalid
    And no role badge is stored

  @ears_event_driven @maintainer @phase_2_7
  Scenario: REQ-HUB-AWARD-009 When a super admin unties a badge from a Discord role, the hub shall stop showing it to the role's members and record that on the audit log
    Given a Discord role named "Sunday Toad"
    And a raider who holds the "Sunday Toad" role
    And a super admin
    When the super admin ties the "sunday-toad" badge to the "Sunday Toad" role
    And the super admin unties the "sunday-toad" badge from the "Sunday Toad" role
    Then the raider has no role badges
    And the audit log records "role_badge.remove"

  @ears_event_driven @maintainer @phase_2_7
  Scenario: REQ-HUB-AWARD-011 When a super admin ties a raid night's badge to a Discord role, the hub shall put everyone holding that role on that night's team with no change to the raid-day config, and take them off it when the badge is untied
    Given a Discord role named "Thursday Toad"
    And a member who holds only the "Thursday Toad" role
    And a super admin
    When the super admin ties the "thursday-toad" badge to the "Thursday Toad" role
    Then the member is on the "thu" raid team
    And the member can tell Thursday's officers they will miss a night
    When the super admin unties the "thursday-toad" badge from the "Thursday Toad" role
    Then the member is on no raid team

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-AWARD-010 A member's own page shall show the toads the header shows beside their name, rank, member toad and role badges included, as badges ahead of their awards
    Given the member's own page
    Then its heading wears the same toads as the header
    And its "Your toads" card shows each of those toads as a badge ahead of the awards
