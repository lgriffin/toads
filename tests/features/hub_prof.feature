# Professions (docs/professions.md): the professions each member picks on Me, and the members officers name as the
# guild's crafters, the people the guild sends its top end recipes to. Listing who crafts what to every member comes
# later, with the bank's recipe data.
Feature: HUB PROF

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-PROF-001 When a member picks their professions on Me, the hub shall store each with its optional skill and specialisation and read them back to that member
    Given a Wednesday raider
    When the raider picks "alchemy" at 375 as "transmute" and "herbalism"
    Then their professions read back as "alchemy" at 375 as "transmute" and "herbalism"

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-002 A raid night's officers shall see the professions of every member on that night, and another night's officers shall be refused them
    Given a Wednesday raider
    And a Wednesday officer
    And a Sunday officer
    When the raider picks "alchemy" at 375 as "transmute" and "herbalism"
    Then the Wednesday officer sees the raider with "alchemy" and "herbalism"
    And the Sunday officer is refused Wednesday's professions

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-003 When a raid night's officer names one of that night's members a guild crafter for a profession they list, the hub shall list them among the guild's crafters, show it on their Me and record it on the audit log
    Given a Wednesday raider
    And a Wednesday officer
    When the raider picks "alchemy" at 375 as "transmute" and "herbalism"
    And the Wednesday officer names the raider the guild's "alchemy" crafter for "Flasks"
    Then the guild's crafters include the raider for "alchemy"
    And the raider's Me shows them as the guild's "alchemy" crafter
    And the audit log records "crafter.name"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-004 If an officer names a member for a profession they do not list, or a member of a night the officer does not run, then the hub shall refuse it
    Given a Wednesday raider
    And a Wednesday officer
    And a Sunday officer
    When the raider picks "alchemy" at 375 as "transmute" and "herbalism"
    Then the Wednesday officer naming the raider for "tailoring" is refused
    And the Sunday officer naming the raider for "alchemy" is refused

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-PROF-005 When a guild crafter stops listing that profession on Me, the hub shall end their naming for it
    Given a Wednesday raider
    And a Wednesday officer
    When the raider picks "alchemy" at 375 as "transmute" and "herbalism"
    And the Wednesday officer names the raider the guild's "alchemy" crafter for "Flasks"
    And the raider drops every profession
    Then the guild's crafters do not include the raider
