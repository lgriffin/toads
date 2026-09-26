# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB CLAIM

  @ears_event_driven @member @phase_2_2 @pending
  Scenario: REQ-HUB-CLAIM-001 When a member claims a character whose name matches their server nickname, the hub shall approve the claim without officer action

  @ears_state_driven @member @phase_2_3 @pending
  Scenario: REQ-HUB-CLAIM-002 While a member has no approved claim, the /me page shall show the claim flow and no performance data

  @ears_event_driven @raid_leader @phase_2_2 @pending
  Scenario: REQ-HUB-CLAIM-003 When a claim needs approval, the hub shall notify #officers and let an officer approve, reject with a reason, or reassign in one action
