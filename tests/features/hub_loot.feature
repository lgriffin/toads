# Officers' loot priority (docs/loot.md): each raid night's officers keep a list of the big-ticket items they decide
# on, put the night's raiders in line for each one first, second, third, and mark each one received.
Feature: HUB LOOT

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-001 When a raid night's officer searches for an item by name, the hub shall offer matching items from its item catalogue, best quality first, each with its item id
    Given a Wednesday officer
    When the Wednesday officer searches the items for "thunderfury"
    Then the first item offered is "Thunderfury, Blessed Blade of the Windseeker" with id 19019
    And a search of one letter is refused

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-002 When an officer adds an item and ranks members of that night's raid group for it, the hub shall show the item by its canonical name with the line in rank order to every officer of that night, and record it on the audit log
    Given a Wednesday officer
    And Wednesday raiders "Hopscotch", "Lilypad" and "Toadstool"
    When the Wednesday officer adds item 19019 to Wednesday's loot list
    And puts "Lilypad", "Hopscotch" and "Toadstool" in line for it
    Then another Wednesday officer sees "Thunderfury, Blessed Blade of the Windseeker" with "Lilypad", "Hopscotch" and "Toadstool" in line
    And "Lilypad" is next up
    And the audit log records "loot.add" and "loot.line" for Wednesday

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-003 When an officer marks the first in line received, the hub shall make the next one in line next up, and unmarking shall put them back
    Given a Wednesday officer
    And Wednesday raiders "Hopscotch", "Lilypad" and "Toadstool"
    And item 19019 on Wednesday's loot list with "Lilypad", "Hopscotch" and "Toadstool" in line
    When the Wednesday officer marks "Lilypad" received
    Then "Hopscotch" is next up
    And "Lilypad" has received it
    And after "Lilypad" is unmarked "Lilypad" is next up again

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-004 If an officer puts someone outside that night's raid group in line, adds an item the catalogue lacks or adds an item twice, then the hub shall refuse it and change nothing
    Given a Wednesday officer
    And Wednesday raiders "Hopscotch", "Lilypad" and "Toadstool"
    And a Sunday raider "Bogwalker"
    And item 19019 on Wednesday's loot list with "Lilypad", "Hopscotch" and "Toadstool" in line
    When the Wednesday officer puts "Bogwalker" in line for it
    Then the request is refused as unprocessable
    And adding item 999999999 is refused as unprocessable
    And adding item 19019 again is refused as a conflict
    And Wednesday's loot list still holds one item with "Lilypad", "Hopscotch" and "Toadstool" in line

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-005 If a raider or another raid night's officer asks for a night's loot list or tries to change it, then the hub shall refuse it and change nothing
    Given a Wednesday officer
    And Wednesday raiders "Hopscotch", "Lilypad" and "Toadstool"
    And item 19019 on Wednesday's loot list with "Lilypad", "Hopscotch" and "Toadstool" in line
    When a Sunday officer asks for Wednesday's loot list
    Then the request is refused as forbidden
    And a Wednesday raider cannot see or change Wednesday's loot list
    And a global officer sees Wednesday's loot list
    And Wednesday's loot list still holds one item with "Lilypad", "Hopscotch" and "Toadstool" in line

  @ears_ubiquitous @raid_leader @phase_2_7
  Scenario: REQ-HUB-LOOT-006 Each raid night's own officer section shall hold that night's loot list, with each item linked to its Wowhead page
    Given the night's officer section
    Then it holds the night's loot list
    And each loot item links to Wowhead by its item id
