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

  @ears_ubiquitous @raid_leader @phase_2_7 @pending
  Scenario: REQ-HUB-BOARD-006 The Raid page shall show the selected raid night's task board to that night's officers only
