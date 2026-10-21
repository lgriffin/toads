# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB ME

  @ears_event_driven @member @phase_2_4 @pending
  Scenario: REQ-HUB-ME-001 When a raid analysis completes, the hub shall send each claimed character's owner a Discord DM with two headline numbers and a link, within 5 minutes

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-ME-002 The /me page shall show a member's primary metric per raid against the guild median for the same role, never against all players
    Given a Wednesday raider signed in to the hub
    And they hold an approved claim on "Lilypad"
    When the worker publishes a character page where "Lilypad" healed 1100000 against a healer median of 1000000
    Then their raids show "Lilypad" healing 1100000 against the healer median of 1000000
    And a member without a claim on "Lilypad" sees no raids

  @ears_ubiquitous @member @phase_2_3 @pending
  Scenario: REQ-HUB-ME-003 Every chart on /me shall be legible without horizontal scrolling at 390 px width

  @ears_state_driven @member @phase_2_3
  Scenario: REQ-HUB-ME-004 While a member has fewer than three analysed raids, the /me page shall show a "building your history" state instead of trend lines
    Given the raids card on Me
    Then it draws trend lines only from 3 guild raids
    And below that it says the history is building

  @ears_optional @member @phase_2_3
  Scenario: REQ-HUB-ME-005 Where a member has more than one character with guild raids, the /me page shall let them switch between those characters' raids, and never to a character that is not theirs
    Given a Wednesday raider signed in to the hub
    And they hold an approved claim on "Lilypad"
    And they hold an approved claim on "Ribbit"
    When the worker publishes character pages for "Lilypad", "Ribbit" and "Bogwalker"
    Then they can switch between the raids of "Lilypad" and "Ribbit"
    And asking for "Bogwalker" shows "Lilypad" instead

  @ears_state_driven @member @phase_2_3
  Scenario: REQ-HUB-ME-006 While a member holds more than one approved character, the /me page shall open on their main and switch to any of their characters from one dropdown that names the main
    Given a Wednesday raider signed in to the hub
    And they hold an approved claim on "Ribbit"
    And they hold an approved claim on "Lilypad"
    When the worker publishes character pages for "Lilypad", "Ribbit" and "Bogwalker"
    Then their raids open on their main "Ribbit" with "Lilypad" after it
    And the raids card picks characters from a dropdown that names the main
