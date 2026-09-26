# Recruitment: applying from the hub and talking it through in a private Discord interview room.
Feature: HUB RECRUIT

  @ears_event_driven @member @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-001 When someone in the Toads Discord applies, the hub shall record the application and show it to the officers of the raid days they applied for and to the global tier
    Given the demo guild
    When the applicant applies for Wednesday
    Then the Wednesday officer and the global officer see the application
    And the Sunday officer does not

  @ears_event_driven @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-002 When an officer opens an interview room, the bot shall create a private Discord channel that only the applicant, that raid day's officers, the global tier and the bot can see
    Given the demo guild
    And the applicant has applied for Wednesday
    When the Wednesday officer opens an interview room
    Then the application is being interviewed
    And the bot is asked for a room for the applicant with the Wednesday and global officer roles only
    And the bot creates a channel hidden from everyone else

  @ears_event_driven @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-003 When an application with an interview room is accepted, declined or withdrawn, the bot shall lock the room so the applicant can read but not post and the officers keep the transcript
    Given the demo guild
    And the applicant has applied for Wednesday
    And the Wednesday officer has opened an interview room
    When the Wednesday officer declines the application
    Then the bot is asked to lock the interview room
    And the bot leaves the applicant able to read but not post

  @ears_unwanted_behavior @raid_leader @maintainer @phase_2_4
  Scenario: REQ-HUB-RECRUIT-004 If an officer requests a status change the application pipeline does not allow, then the hub shall refuse it with 409
    Given the demo guild
    And the applicant has applied for Wednesday
    Then accepting straight from applied is refused with 409
    And every pair of statuses outside the pipeline is refused

  @ears_unwanted_behavior @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-005 If an applicant already has an open application, or was declined in the last 30 days, then the hub shall refuse a new application
    Given the demo guild
    And the applicant has applied for Wednesday
    Then a second application is refused with 409
    When the Wednesday officer declines the application
    Then a new application 29 days later is refused with 409
    And a new application 31 days later is accepted

  @ears_ubiquitous @member @maintainer @phase_2_4
  Scenario: REQ-HUB-RECRUIT-006 The application shall ask only for game details and never for age, email address or real name
    Then the application form's fields are character, class, spec, role, raid days, experience, availability and a Warcraft Logs link
    And a Warcraft Logs link must be an https link to warcraftlogs.com
