# The raid leader desk on the inward hub: what is waiting on an officer.
Feature: HUB DESK

  @ears_ubiquitous @raid_leader @phase_2_3
  Scenario: REQ-HUB-DESK-001 The raid leader desk shall count the applications, Discord posts, clips and spotlights waiting on an officer, limited to that officer's raid days
    Given the demo guild
    And the applicant has applied for Sunday
    And a Wednesday Discord message is waiting for review
    Then the Wednesday officer's desk shows no applications and one post to curate
    And the Sunday officer's desk shows one application
