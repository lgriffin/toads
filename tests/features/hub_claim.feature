# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB CLAIM

  @ears_event_driven @member @phase_2_2
  Scenario: REQ-HUB-CLAIM-001 When a member claims a character whose name matches their server nickname, the hub shall approve the claim without officer action
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    When they claim the character "Hopscotch"
    Then the claim is approved
    And #officers only gets an FYI they can reassign from

  @ears_state_driven @member @phase_2_3 @pending
  Scenario: REQ-HUB-CLAIM-002 While a member has no approved claim, the /me page shall show the claim flow and no performance data

  @ears_event_driven @raid_leader @phase_2_2
  Scenario Outline: REQ-HUB-CLAIM-003 When a claim needs approval, the hub shall notify #officers and let an officer approve, reject with a reason, or reassign in one action
    Given a Wednesday raider signed in with server nickname "Hops"
    When they claim the character "Hopscotch"
    Then the claim is pending
    And #officers is notified of the claim
    When a Wednesday officer decides to <action> the claim
    Then the claim ends <outcome>
    And the decision is in the audit log for raid day "wed"

    Examples:
      | action   | outcome                         |
      | approve  | approved                        |
      | reject   | rejected with the reason        |
      | reassign | approved for the other member   |

  @ears_event_driven @member @phase_2_2
  Scenario: REQ-HUB-CLAIM-004 When a signed-in member searches for a character by name, the hub shall list the matching characters seen in the guild's logs, so a claim never asks for an id or for who the member is
    Given a Wednesday raider signed in with server nickname "Hops"
    When they search for characters named "scotch"
    Then they are offered "Hopscotch" and "Höpscotch"

  @ears_state_driven @raid_leader @phase_2_2
  Scenario: REQ-HUB-CLAIM-005 While a claim waits for an officer, the hub shall list it on the claims panel of each raid night the claimant's Discord roles put them on, and on the global officers' list when they hold no night
    Given a Wednesday raider signed in with server nickname "Hops"
    And they claim the character "Hopscotch"
    Then the Wednesday officers' claims panel lists the claim with the claimant's name
    And the Sunday officers' claims panel does not list it
    And the global officers' no-night list does not list it
