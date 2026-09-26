# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB PRIV

  @ears_ubiquitous @member @phase_2_2 @pending
  Scenario: REQ-HUB-PRIV-001 The hub shall show a member's per-raid detail only to that member and to officers, unless the member has enabled a public profile

  @ears_optional @member @phase_2_6 @pending
  Scenario: REQ-HUB-PRIV-002 Where a member has enabled a public profile, raiders shall be able to open that member's page from Compare

  @ears_event_driven @member @phase_2_2 @pending
  Scenario: REQ-HUB-PRIV-003 When a member unclaims a character, the hub shall detach the member from it immediately while keeping the raid rows
