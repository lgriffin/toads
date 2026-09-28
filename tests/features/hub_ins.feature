# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB INS

  @ears_ubiquitous @raid_leader @phase_2_2 @phase_2_6
  Scenario: REQ-HUB-INS-001 GM/RL insights, boss insights and reference comparisons shall be visible only to officers
    Given a Wednesday officer signed in to the hub
    Then they can open the Wednesday reference comparison
    And a Wednesday raider cannot open it
    And a Sunday officer cannot open it

  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-INS-002 When an officer selects two raids, the hub shall show the raid diff the desktop app produces today

  # Reference comparison through the dedicated Warcraft Logs login. Added with the reference page; not yet in the
  # build spec's tables.
  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-INS-003 When an officer connects the guild's Warcraft Logs account, the hub shall keep its token encrypted as the dedicated login for importing reference reports
    Given a Wednesday officer signed in to the hub
    When they connect the guild's Warcraft Logs account
    Then the reference page shows the account connected by them
    And the database does not hold the token in plain text

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-INS-004 When an officer imports another guild's report or compares one of our raids with a reference, the hub shall queue the work for the worker and show its progress
    Given a Wednesday officer signed in to the hub
    And they connect the guild's Warcraft Logs account
    When they import another guild's report as a reference
    And they compare one of our raids with it
    Then both requests are queued for the worker
    And the reference page lists both as queued

  @ears_unwanted_behavior @raid_leader @phase_2_6
  Scenario: REQ-HUB-INS-005 If no Warcraft Logs account is connected, then the hub shall refuse to import a reference report and ask an officer to connect one
    Given a Wednesday officer signed in to the hub
    When they import another guild's report as a reference
    Then the import is refused with 409
