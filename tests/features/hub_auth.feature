# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB AUTH

  @ears_ubiquitous @member @phase_2_2
  Scenario: REQ-HUB-AUTH-001 The hub shall authenticate members only through Discord; no hub-specific password shall exist
    Given the hub API
    Then signing in redirects to Discord with a PKCE challenge
    And no route or table holds a hub password

  @ears_unwanted_behavior @member @phase_2_2
  Scenario: REQ-HUB-AUTH-002 If a signed-in Discord user is not a member of the Toads server, then the hub shall show a "members only" page and create no session
    Given a Discord user who is not in the Toads server
    When they complete Discord sign-in
    Then the hub sends them to the members only page
    And no session is created
