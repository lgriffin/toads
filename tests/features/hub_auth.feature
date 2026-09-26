# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB AUTH

  @ears_ubiquitous @member @phase_2_2 @pending
  Scenario: REQ-HUB-AUTH-001 The hub shall authenticate members only through Discord; no hub-specific password shall exist

  @ears_unwanted_behavior @member @phase_2_2 @pending
  Scenario: REQ-HUB-AUTH-002 If a signed-in Discord user is not a member of the Toads server, then the hub shall show a "members only" page and create no session
