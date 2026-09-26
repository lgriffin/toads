# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB ME

  @ears_event_driven @member @phase_2_4 @pending
  Scenario: REQ-HUB-ME-001 When a raid analysis completes, the hub shall send each claimed character's owner a Discord DM with two headline numbers and a link, within 5 minutes

  @ears_ubiquitous @member @phase_2_3 @pending
  Scenario: REQ-HUB-ME-002 The /me page shall show a member's primary metric per raid against the guild median for the same role, never against all players

  @ears_ubiquitous @member @phase_2_3 @pending
  Scenario: REQ-HUB-ME-003 Every chart on /me shall be legible without horizontal scrolling at 390 px width

  @ears_state_driven @member @phase_2_3 @pending
  Scenario: REQ-HUB-ME-004 While a member has fewer than three analysed raids, the /me page shall show a "building your history" state instead of trend lines
