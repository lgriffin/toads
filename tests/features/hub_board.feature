# The officers' task board (docs/officer-board.md): one Trello-style board per raid night, on the Raid page, for that
# night's officers to assign tasks, set due dates and track the guild's internal work around the raid.
Feature: HUB BOARD

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-001 When a raid day's officer adds a card to that day's board, the hub shall show it to every officer of that day with its assignee and due date, and record it on the audit log
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    When the Wednesday officer adds "Book the Gruul pug tank" for the raider due "2026-10-21" to Wednesday's board
    Then Wednesday's board shows "Book the Gruul pug tank" in "To do" assigned to "Hopscotch" due "2026-10-21"
    And the audit log records "board.add" for Wednesday

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-002 When an officer moves a card to another lane or place, the hub shall keep every other card on the board in its order
    Given a Wednesday officer
    And Wednesday's board holds "Flasks", "Drums" and "Soulstones" in "To do"
    When the Wednesday officer moves "Soulstones" to the top of "In progress"
    And the Wednesday officer moves "Flasks" to the top of "In progress"
    Then "To do" holds just "Drums"
    And "In progress" holds "Flasks" then "Soulstones"

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-003 If a raider or another raid day's officer asks for a raid day's board or tries to change it, then the hub shall refuse it and change nothing
    Given a Wednesday officer
    And Wednesday's board holds "Flasks", "Drums" and "Soulstones" in "To do"
    When a Sunday officer asks for Wednesday's board
    Then the request is refused as forbidden
    And a Wednesday raider cannot see or change Wednesday's board
    And Wednesday's board still holds 3 cards

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-004 Each raid day shall have its own board, and global officers and super admins shall work every day's board
    Given a Wednesday officer
    And Wednesday's board holds "Flasks", "Drums" and "Soulstones" in "To do"
    When a global officer adds "Post the Sunday roster" to Sunday's board
    Then Sunday's board holds only "Post the Sunday roster"
    And the global officer sees 3 cards on Wednesday's board

  @ears_state_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-005 While a card's due date has passed and it is not in Done, the hub shall mark it overdue
    Given a Wednesday officer
    When the Wednesday officer adds "Restock the bank" due yesterday to Wednesday's board
    Then the card "Restock the bank" is overdue
    And after it moves to "Done" it is not overdue

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-006 Each raid night's own officer section shall hold that night's task board, absences and interview panel, shown to that night's officers only, and the shared Officer console and the Raid page shall link only the nights the viewer runs
    Given the night's officer section
    Then it holds the night's task board, absences and interview panel
    And it shows them only to that night's officers
    And the Raid page's officer desk links to it instead of holding the board
    And the Officer console lists only the nights the viewer runs

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BOARD-007 When a raid night's officer pins a strategy or role link, the hub shall show it at the top of that night's officer section with who is away from the next night, to that night's officers only
    Given a Wednesday officer
    When the Wednesday officer pins "Kael'thas strategy" at "https://docs.google.com/document/d/abc"
    Then another Wednesday officer sees "Kael'thas strategy" pinned on Wednesday
    And the audit log records "board.link_add" for Wednesday
    And a link that is not https is refused
    And a Sunday officer cannot see or pin Wednesday's links
    And the night's officer section opens with the next night, who is away and the pinned links
