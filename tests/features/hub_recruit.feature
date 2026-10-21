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
  Scenario: REQ-HUB-RECRUIT-003 When an application with an interview room is accepted or withdrawn, the bot shall lock the room so the applicant can read but not post and the officers keep the transcript
    Given the demo guild
    And the applicant has applied for Wednesday
    And the Wednesday officer has opened an interview room
    When the applicant withdraws the application
    Then the bot is asked to lock the interview room
    And the bot leaves the applicant able to read but not post

  @ears_unwanted_behavior @raid_leader @maintainer @phase_2_4
  Scenario: REQ-HUB-RECRUIT-004 If an officer requests a status change the application pipeline does not allow, then the hub shall refuse it with 409
    Given the demo guild
    And the applicant has applied for Wednesday
    Then offering a trial straight from applied is refused with 409
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
    Then the application asks for character, class, primary role, secondary role and why Toads, with spec, raid days, experience, availability and a Warcraft Logs link as optional extras
    And a Warcraft Logs link must be an https link to warcraftlogs.com

  @ears_ubiquitous @raid_leader @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-007 Applications, their status history, posts, highlights and spotlights shall be kept in the hub database, so an API restart loses nothing
    Given the demo guild stored in the hub database
    And the applicant has applied for Wednesday
    When the Wednesday officer declines the application
    And the API restarts
    Then the application is still declined with its full history

  @ears_state_driven @member @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-008 While interviewers are named in the community config, when someone applies, the bot shall open their interview room straight away with only the applicant, those interviewers and the bot in it, and post the answers there
    Given the demo guild with interviewers _gallagher and hadur117
    When the applicant applies for Wednesday
    Then the application is being interviewed
    And the bot is asked for a room for the applicant with _gallagher and hadur117 and no officer roles
    And the bot creates the room for the applicant and the two interviewers with the answers in it

  @ears_unwanted_behavior @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-009 If someone who is not in the Toads Discord server sends an application, then the hub shall refuse it with 403 and record nothing
    Given the demo guild
    When an applicant who has left the Toads Discord sends an application
    Then the application is refused with 403 asking them to join the Discord
    And no application or interview room is recorded

  @ears_event_driven @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-010 When someone signs in with Discord from the recruit page, the hub shall bring them back to the recruit page, and shall return to no page outside its fixed list
    When a Toads Discord member signs in from the recruit page
    Then they land back on the recruit page
    And a sign-in that asks to return to another site lands on the hub home

  @ears_unwanted_behavior @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-011 If someone applies from a Discord account less than 7 days old, then the hub shall refuse the application with 409 and say when they can apply
    Given the demo guild
    When an applicant whose Discord account is 2 days old applies for Wednesday
    Then the application is refused with 409 naming the day they can apply
    And no application or interview room is recorded
    And the same applicant is accepted once the account is 7 days old

  @ears_unwanted_behavior @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-012 If an applicant has sent 3 applications in the last 7 days, then the hub shall refuse another one with 409, so withdrawing and reapplying cannot keep opening interview rooms
    Given the demo guild
    And the applicant has applied and withdrawn 3 times today
    Then a fourth application is refused with 409
    And an application 8 days later is accepted

  @ears_event_driven @member @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-013 When someone applies for a raid night whose officers have set an interview panel, the bot shall open their interview room straight away with only the applicant, that night's panel and the bot in it
    Given the demo guild with interviewers _gallagher and hadur117
    And the Sunday officer has put croakley and pondkeeper from the Discord on the Sunday interview panel
    When the applicant applies for Sunday
    Then the application is being interviewed
    And the bot is asked for a room for the applicant with croakley and pondkeeper by Discord id and no officer roles
    And a Wednesday applicant still gets _gallagher and hadur117

  @ears_ubiquitous @raid_leader @maintainer @phase_2_4
  Scenario: REQ-HUB-RECRUIT-014 Only a raid night's officers, the global tier and super admins shall see or change that night's interview panel, and every change shall be on the audit log
    Given the demo guild
    When the Wednesday officer tries to put croakley on the Sunday interview panel
    Then the hub refuses it with 403
    And the global officer can put croakley on the Sunday interview panel
    And the audit log names the Sunday panel change

  @ears_ubiquitous @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-015 The application shall take a WoW Forever character name of one or more words split by a single space, trimmed and with repeated spaces collapsed, and refuse names with digits, symbols or other whitespace
    Given the demo guild
    When the applicant applies for Wednesday as "  Big   Toad "
    Then the application is recorded for "Big Toad"
    And the names "Big Toad2", "Big-Toad" and "Big_Toad" are refused

  @ears_unwanted_behavior @member @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-016 If the bot cannot open an interview room for a reason retrying will not fix, then the hub shall record why on the application, show it to the applicant and the officers, and let an officer ask for the room again
    Given the demo guild with interviewers _gallagher and hadur117
    And the applicant has applied for Wednesday
    When the bot reports that it needs Manage Roles to open the room
    Then the applicant's application says the room could not open because the bot needs Manage Roles
    And the Wednesday officer can ask for the room again, which clears the reason

  @ears_event_driven @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-017 When the bot has opened an applicant's interview room, the hub shall give the applicant a link straight into that room, and no link before it exists
    Given the demo guild with interviewers _gallagher and hadur117
    And the applicant has applied for Wednesday
    Then the applicant's application has no room link
    When the bot reports the room it opened
    Then the applicant's application links to that room in the Toads Discord

  @ears_ubiquitous @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-018 A raid night's Decisions panel shall list the applications for that night waiting on a decision, with every officer's notes on them, and only that night's officers, the global tier and super admins shall see it or add notes
    Given the demo guild
    And the applicant has applied for Wednesday
    When the Wednesday officer notes "Strong healer, logs look good"
    And the global officer notes "Free on Wednesdays"
    Then the Wednesday Decisions panel lists the application with both notes, oldest first
    And the Sunday officer can neither see the application on the Sunday panel nor note it
    And the applicant's own view of the application carries no notes

  @ears_event_driven @raid_leader @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-019 When an officer rejects an application on the Decisions panel, the hub shall decline it, take it off the waiting list and have the bot delete its interview room
    Given the demo guild
    And the applicant has applied for Wednesday
    And the Wednesday officer has opened an interview room
    When the Wednesday officer rejects the application on the Decisions panel
    Then the application is declined and listed as decided, not waiting
    And the bot is asked to delete the interview room
    And the bot deletes the channel
    And a second decision on it is refused with 409

  @ears_event_driven @raid_leader @member @phase_2_4
  Scenario: REQ-HUB-RECRUIT-020 When an officer accepts an application on the Decisions panel, the hub shall accept it for that night and the bot shall give the applicant the night's raider roles and welcome them in their room, and the panel shall show what the bot did
    Given the demo guild with Wednesday raider role 41 and role 42 tied to the Wednesday Toad badge
    And the applicant has applied for Wednesday
    And the Wednesday officer has opened an interview room
    When the Wednesday officer accepts the application on the Decisions panel
    Then the application is accepted for Wednesday
    And the bot is asked to give the applicant roles 41 and 42 and welcome them in the interview room
    And the bot gives the roles and posts the welcome
    And once the bot reports it, the Decisions panel notes that the Toad Bot gave the Wednesday raider role

  @ears_unwanted_behavior @raid_leader @phase_2_4
  Scenario: REQ-HUB-RECRUIT-021 If an application is accepted for a night with no Discord raider role set, or the bot cannot give the role, then the hub shall say so in a note on the Decisions panel, so an officer gives it by hand
    Given the demo guild
    And the applicant has applied for Wednesday
    When the Wednesday officer accepts the application on the Decisions panel
    Then the Decisions panel notes that no Discord role is set for Wednesday raiders
    And the bot is not asked to give any role
