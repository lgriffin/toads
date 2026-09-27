# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB PRIV

  @ears_ubiquitous @member @phase_2_2 @pending
  Scenario: REQ-HUB-PRIV-001 The hub shall show a member's per-raid detail only to that member and to officers, unless the member has enabled a public profile

  @ears_optional @member @phase_2_6 @pending
  Scenario: REQ-HUB-PRIV-002 Where a member has enabled a public profile, raiders shall be able to open that member's page from Compare

  @ears_event_driven @member @phase_2_2
  Scenario: REQ-HUB-PRIV-003 When a member unclaims a character, the hub shall detach the member from it immediately while keeping the raid rows
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    And they claim the character "Hopscotch"
    When they unclaim it
    Then they no longer hold the claim
    And the character can be claimed again

  # Added in phase 2.2 for the community layer; not yet in the build spec's tables.
  @ears_ubiquitous @member @phase_2_2
  Scenario: REQ-HUB-PRIV-004 The hub shall let every signed-in member list hub members by display name, and shall show Discord user ids to officers only
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    And a Wednesday officer signed in
    When the raider lists the members
    Then they see "Hopscotch" and no Discord user ids
    When the officer lists the members
    Then they see every member's Discord user id
    And signed-out visitors cannot list the members

  # Added for member settings; not yet in the build spec's tables.
  @ears_optional @member @phase_2_2
  Scenario: REQ-HUB-PRIV-005 Where a member has chosen one of their approved characters as their name, the hub shall show that name in place of their server nickname for as long as they hold the claim
    Given a Wednesday raider signed in with server nickname "Hops"
    And they claim the character "Ribbit"
    And a Wednesday officer approves the claim
    When they choose "Ribbit" as their name
    Then the members list and their session show "Ribbit"
    And they cannot choose a character they have not claimed
    When they unclaim it
    Then the members list and their session show "Hops"
