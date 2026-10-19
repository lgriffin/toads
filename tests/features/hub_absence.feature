# Absences (docs/absences.md): a raid day's trials and raiders say which raid nights they will miss on the Calendar
# page, and that raid day's officers see the team's upcoming absences in one place.
Feature: HUB ABSENCE

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-ABSENCE-001 When a raider reports an absence from their raid day's team, the hub shall list it among their absences with the raid nights it covers and show it to that raid day's officers on each of those nights
    Given today is "2026-10-19"
    And a Wednesday raider "Hopscotch"
    And a Wednesday officer
    When the raider reports an absence from Wednesday from "2026-10-28" to "2026-11-04" saying "Half-term holiday"
    Then the raider's absences cover the nights "2026-10-28, 2026-11-04"
    And the Wednesday officer sees "Hopscotch" away on "2026-10-28" and "2026-11-04" saying "Half-term holiday"
    And the Wednesday officer sees nobody away on "2026-10-21"

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-ABSENCE-002 If a member reports an absence from a raid day's team they hold no trial, raider or officer role on, then the hub shall refuse it and store nothing
    Given today is "2026-10-19"
    And a Wednesday raider "Hopscotch"
    When the raider reports an absence from Sunday from "2026-10-25" to "2026-10-25" saying "Away"
    Then the request is refused as forbidden
    And no absence is stored

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-ABSENCE-003 If a raider, or an officer of another raid day, asks for a raid day's absences, then the hub shall refuse it; a global officer shall see every raid day's
    Given today is "2026-10-19"
    And a Wednesday raider "Hopscotch"
    And a Sunday officer
    And a global officer
    Then the raider is refused Wednesday's absences
    And the Sunday officer is refused Wednesday's absences
    And the global officer sees Wednesday's and Sunday's absences

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-ABSENCE-004 If an absence starts before today, ends before it starts, holds no raid night of that team, or overlaps one the member already reported, then the hub shall refuse it
    Given today is "2026-10-19"
    And a Wednesday raider "Hopscotch"
    When the raider reports an absence from Wednesday from "2026-10-28" to "2026-10-28" saying "Dentist"
    Then reporting Wednesday from "2026-10-14" to "2026-10-21" is refused as invalid
    And reporting Wednesday from "2026-10-30" to "2026-10-29" is refused as invalid
    And reporting Wednesday from "2026-10-22" to "2026-10-26" is refused as invalid
    And reporting Wednesday from "2026-10-27" to "2026-11-04" is refused as a conflict

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-ABSENCE-005 When a member cancels their own absence, the hub shall remove it from their list and the officers' view; another member's cancel shall find nothing
    Given today is "2026-10-19"
    And a Wednesday raider "Hopscotch"
    And a Wednesday officer
    When the raider reports an absence from Wednesday from "2026-10-21" to "2026-10-21" saying "Late shift"
    Then the Wednesday officer cannot cancel it
    When the raider cancels it
    Then the raider has no absences
    And the Wednesday officer sees nobody away on "2026-10-21"
