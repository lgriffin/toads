# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB HOME

  @ears_event_driven @member @phase_2_4 @pending
  Scenario: REQ-HUB-HOME-001 When an officer creates or edits a Discord scheduled event, the Home page shall show it as the next raid within 5 minutes

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-HOME-002 The hub home shall let each signed-in member choose which widgets it shows and in what order, and shall keep that choice for their next visit
    Given a Wednesday raider signed in to the hub
    When they show only the recruiting and raid totals widgets, recruiting first
    Then their home shows recruiting and then raid totals
    And after signing in again their home still shows recruiting and then raid totals

  @ears_unwanted_behavior @member @phase_2_3
  Scenario: REQ-HUB-HOME-003 If a member without officer powers places the raid leader desk on their home, then the hub shall refuse it and offer them no officer widgets
    Given a Wednesday raider signed in to the hub
    Then their home offers no officer widgets
    And placing the raid leader desk is refused with 403

  @ears_event_driven @member @phase_2_3
  Scenario: REQ-HUB-HOME-004 When a member resets their home, the hub shall show the default widgets again
    Given a Wednesday raider signed in to the hub
    And they show only the recruiting and raid totals widgets, recruiting first
    When they reset their home
    Then their home shows the default widgets

  @ears_event_driven @member @phase_2_3
  Scenario: REQ-HUB-HOME-005 When a member signs in with Discord, the hub shall take them to their hub home rather than the public landing page
    Given a Wednesday raider in the Toads server
    When they complete Discord sign-in
    Then the hub sends them to their hub home

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-HOME-006 The hub home shall show the guild's healing per raid week on week, measured against its four-week average and the guild's target, as the analyzer builds it
    Given a Wednesday raider signed in to the hub
    When the worker publishes the analyzer's weekly healing chart
    Then their home shows weekly healing by default
    And the weekly healing chart carries the four-week average and the target

  @ears_unwanted_behavior @member @phase_2_3
  Scenario: REQ-HUB-HOME-007 If the worker publishes a chart over the chart limits, then the hub shall refuse the whole page
    Given a Wednesday raider signed in to the hub
    When the worker publishes a weekly healing chart with nine series
    Then the page is refused with 422
    And the hub keeps no weekly healing chart
