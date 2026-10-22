# Professions (docs/professions.md): the professions each member picks on Me, and the members officers name as the
# guild's crafters, the people the guild sends its top end recipes to. Listing who crafts what to every member comes
# later, with the bank's recipe data.
Feature: HUB PROF

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-PROF-001 When a member picks their professions on Me, the hub shall store each with its optional skill and specialisation and read them back to that member
    Given a Wednesday raider
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    Then their professions read back as "engineering" at 300 as "goblin" and "herbalism"

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-002 A raid night's officers shall see the professions of every member on that night, and another night's officers shall be refused them
    Given a Wednesday raider
    And a Wednesday officer
    And a Sunday officer
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    Then the Wednesday officer sees the raider with "engineering" and "herbalism"
    And the Sunday officer is refused Wednesday's professions

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-003 When a raid night's officer names one of that night's members a guild crafter for a profession they list, the hub shall list them among the guild's crafters, show it on their Me and record it on the audit log
    Given a Wednesday raider
    And a Wednesday officer
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    And the Wednesday officer names the raider the guild's "engineering" crafter for "Sappers"
    Then the guild's crafters include the raider for "engineering"
    And the raider's Me shows them as the guild's "engineering" crafter
    And the audit log records "crafter.name"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-PROF-004 If an officer names a member for a profession they do not list, or a member of a night the officer does not run, then the hub shall refuse it
    Given a Wednesday raider
    And a Wednesday officer
    And a Sunday officer
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    Then the Wednesday officer naming the raider for "tailoring" is refused
    And the Sunday officer naming the raider for "engineering" is refused

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-PROF-005 When a guild crafter stops listing that profession on Me, the hub shall end their naming for it
    Given a Wednesday raider
    And a Wednesday officer
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    And the Wednesday officer names the raider the guild's "engineering" crafter for "Sappers"
    And the raider drops every profession
    Then the guild's crafters do not include the raider

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-PROF-006 The Raid page shall show a raid night's members the guild's crafters who are on that night, and leave out other nights' crafters
    Given a Wednesday raider
    And a Wednesday officer
    And a Sunday raider who lists "tailoring"
    And a Wednesday trial
    When the raider picks "engineering" at 300 as "goblin" and "herbalism"
    And the Wednesday officer names the raider the guild's "engineering" crafter for "Sappers"
    And a global officer names the Sunday raider the guild's "tailoring" crafter
    Then the Wednesday trial sees the raider as Wednesday's "engineering" crafter for "Sappers"
    And the Wednesday trial does not see the Sunday raider among Wednesday's crafters

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-PROF-007 If a member gives a profession skill above 300, the Classic Forever cap, then the hub shall refuse it
    Given a Wednesday raider
    Then the raider picking "engineering" at 301 is refused
