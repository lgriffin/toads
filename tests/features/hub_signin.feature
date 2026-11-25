# The sign-in audit (docs/sign-ins.md): each time a member signs in to the hub is recorded, and officers see, for a day
# they pick, who signed in and when each member of their raid night last did. A night's officers see only their own
# night's members; the global tier also sees members on no raid night.
Feature: HUB SIGNIN

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-SIGNIN-001 When a member signs in, the hub shall record the sign-in, and their raid night's officers shall see it in that day's sign-ins and as the member's last sign-in
    Given today is "2026-11-25"
    And a Wednesday officer
    And a Wednesday raider "Hopscotch" who signed in on "2026-11-24"
    And a Wednesday raider "Lilypad" who has never signed in
    When "Hopscotch" signs in again on "2026-11-25"
    Then the Wednesday officer sees "Hopscotch" among the sign-ins on "2026-11-25"
    And the Wednesday officer sees "Hopscotch" among the sign-ins on "2026-11-24"
    And the Wednesday officer sees "Hopscotch" last signed in on "2026-11-25" and "Lilypad" never
    And the Wednesday officer counts 2 sign-ins on "2026-11-25"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-SIGNIN-002 If a raider, or an officer of another raid night, asks for a raid night's sign-ins, then the hub shall refuse it; a global officer shall see every raid night's and those of members on no raid night
    Given today is "2026-11-25"
    And a Wednesday raider "Hopscotch" who signed in on "2026-11-25"
    And a member on no raid night "Tadpole" who signed in on "2026-11-25"
    And a Sunday officer
    And a global officer
    Then the raider is refused Wednesday's sign-ins
    And the Sunday officer is refused Wednesday's sign-ins
    And the Sunday officer does not see "Hopscotch" in Sunday's sign-ins
    And the Sunday officer is refused the sign-ins of members on no raid night
    And the global officer sees "Hopscotch" in Wednesday's sign-ins and "Tadpole" among members on no raid night

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-SIGNIN-003 If an officer asks for the sign-ins of a day after today, then the hub shall refuse it as invalid
    Given today is "2026-11-25"
    And a Wednesday officer
    Then the Wednesday officer's sign-ins for "2026-11-26" are refused as invalid
