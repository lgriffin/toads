# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB HOME

  @ears_event_driven @member @phase_2_4
  Scenario: REQ-HUB-HOME-001 When an officer creates or edits a Discord scheduled event, the Home page shall show it as the next raid within 5 minutes
    Given a Wednesday raider signed in to the hub
    And an officer has posted "Karazhan" as a Discord scheduled event for Wednesday evening
    Then their next raid is "Karazhan" on Wednesday with a link to sign up in Discord
    When the officer moves "Karazhan" an hour later
    And 5 minutes pass
    Then their next raid starts an hour later

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

  @ears_state_driven @member @phase_2_3
  Scenario: REQ-HUB-HOME-006 While Discord has no scheduled event coming up, the hub home shall show the next raid from the raid days' configured start times
    Given a Wednesday raider signed in to the hub
    And Discord has no scheduled events
    Then their next raid is the next Wednesday at the configured start time

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-HOME-007 The hub home's Your performance widget shall show the member's main character's primary number in the last analysed raid against the guild median for the same role
    Given a Wednesday raider signed in to the hub
    And they hold an approved claim on the healer "Lilypad"
    When the worker publishes a raid where "Lilypad" healed 900 against a healer median of 700
    Then their performance shows "Lilypad" at 900 healing against a median of 700

  @ears_unwanted_behavior @member @phase_2_3
  Scenario: REQ-HUB-HOME-008 If another member claims the character named like a member's server nickname, then the hub shall not show that character's numbers on the member's Your performance widget
    Given a Wednesday raider nicknamed "Croak" signed in to the hub
    And another member holds an approved claim on "Croak"
    When the worker publishes a raid with "Croak" in it
    Then their performance shows no character

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-HOME-009 The hub home shall show the guild's healing per raid and average healing per character week on week, each measured against its own four-week average, as the analyzer builds them
    Given a Wednesday raider signed in to the hub
    When the worker publishes the analyzer's weekly healing chart
    Then their home shows weekly healing by default
    And the weekly healing chart carries the four-week average and no target

  @ears_unwanted_behavior @member @phase_2_3
  Scenario: REQ-HUB-HOME-010 If the worker publishes a chart over the chart limits, then the hub shall refuse the whole page
    Given a Wednesday raider signed in to the hub
    When the worker publishes a weekly healing chart with nine series
    Then the page is refused with 422
    And the hub keeps no weekly healing chart

  @ears_ubiquitous @member @phase_2_3
  Scenario: REQ-HUB-HOME-011 The hub shall show each member their main character's Toads badges, earned or not, as the analyzer awards them
    Given a Wednesday raider signed in to the hub
    And they hold an approved claim on the healer "Lilypad"
    When the worker publishes badges where "Lilypad" has the Epic Loyal Toad badge
    Then their badges show "Lilypad" with the Epic Loyal Toad badge

  @ears_unwanted_behavior @raid_leader @phase_2_3
  Scenario: REQ-HUB-HOME-012 If a member without officer powers loads the analyzer's home widgets, then the hub shall leave out the last raid's badge roster that raid leaders see
    Given a Wednesday raider signed in to the hub
    And a Sunday officer signed in to the hub
    When the worker publishes the last raid's badge roster
    Then the officer's home offers the badge roster with "Hopscotch" in it
    And the raider receives no badge roster

  @ears_optional @member @phase_2_3
  Scenario: REQ-HUB-HOME-013 Where a member places the flasks widget, the hub home shall show who in the last raid came prepared with a flask or an elixir pair, as the analyzer builds it
    Given a Wednesday raider signed in to the hub
    When they place the flasks widget
    And the worker publishes the last raid's flasks table with "Hopscotch" on a flask
    Then their home shows "Hopscotch" prepared with a flask
