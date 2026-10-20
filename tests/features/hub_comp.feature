# Raid comps (docs/comps.md): the primary and secondary spec each member sets on Me, and the comps a raid night's
# officers build from that night's roster and lock in.
Feature: HUB COMP

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-COMP-001 When a member sets their class with a primary spec and an optional secondary spec of that class, the hub shall store them and read them back to that member only
    Given a Wednesday raider
    When the raider sets their specs to "shaman-elemental" and "shaman-restoration"
    Then their specs read back as "shaman-elemental" and "shaman-restoration"

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-COMP-002 If a member chooses a spec of another class, or the same spec twice, then the hub shall refuse it and keep their saved specs
    Given a Wednesday raider
    When the raider sets their specs to "shaman-elemental" and "shaman-restoration"
    And the raider tries to set their specs to "shaman-elemental" and "mage-frost"
    Then the request is refused as invalid
    And their specs read back as "shaman-elemental" and "shaman-restoration"

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-003 The comp builder's roster for a raid night shall list every member whose Discord roles put them on that night, with the specs they set, so officers can find who plays a spec as a primary or a secondary
    Given a Wednesday raider
    And a Sunday raider
    And a Wednesday officer
    When the raider sets their specs to "shaman-restoration" and "shaman-elemental"
    Then the Wednesday officer's roster lists the Wednesday raider with "shaman-restoration" and "shaman-elemental"
    And the Wednesday officer's roster does not list the Sunday raider

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-006 The comp builder's roster for a raid night shall list everyone in the Discord server holding that night's roles, marking those who have never signed in to the hub
    Given a Wednesday officer
    And a Wednesday raider who has never signed in to the hub
    Then the Wednesday officer's roster lists the raider who has never signed in, marked as not signed in

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-004 When a raid night's officer locks in a comp, the hub shall store it for that night with its seats and record it on the audit log
    Given a Wednesday raider
    And a Wednesday officer
    When the Wednesday officer locks in "Molten Core" seating the raider as "shaman-elemental"
    Then Wednesday's comps include "Molten Core" with the raider as "shaman-elemental"
    And the audit log records "comp.save"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-005 If a raider or another night's officer asks for a raid night's roster or comps, then the hub shall refuse it
    Given a Wednesday raider
    And a Sunday officer
    Then the raider is refused Wednesday's roster
    And the Sunday officer is refused Wednesday's roster

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-007 When a raid night's officer imports a Raid-Helper export, the hub shall pre-fill the specs of everyone it seats who is in the Discord server, marked as imported, and keep the specs members chose themselves
    Given a Sunday officer
    And a Sunday raider who has never signed in to the hub
    And a Sunday raider who set their own specs to "mage-frost"
    When the Sunday officer imports a Raid-Helper export seating both raiders as "Tank" "Protection1"
    Then the raider who never signed in is on Sunday's roster as "paladin-protection"
    And the raider who set their own specs is still "mage-frost"
    And the audit log records "specs.import"

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-COMP-008 When a member whose specs were imported signs in, the hub shall show them as imported with the class and role badges their primary spec earns, until the member saves their own
    Given a Sunday officer
    And a Sunday raider who has never signed in to the hub
    When the Sunday officer imports a Raid-Helper export seating the raider as "Priest" "Holy"
    And the raider signs in
    Then their specs read back as "priest-holy", marked as imported
    And their badges include "priest" and "healer"
    When the raider confirms their specs
    Then their specs read back as "priest-holy", not marked as imported

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-COMP-009 If someone who is not the raid night's officer sends the Toad Bot a Raid-Helper export for that night, then the hub shall refuse it and change no specs
    Given a Sunday raider who has never signed in to the hub
    And a Wednesday officer
    When the Wednesday officer sends the Toad Bot a Sunday export seating the raider as "Priest" "Holy"
    Then the import is refused
    And the raider has no specs
