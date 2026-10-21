# The bank request desk (docs/bank-desk.md): members ask the guild bank for an item with the Toad Bot's /bankrequest
# (or on the site), officers approve or deny each request with a message on the Bank page, and the Toad Bot DMs the
# member the answer. It needs no bank snapshot, so officers can work it before the bank's stock is imported.
Feature: HUB BDESK

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-BDESK-001 When a member asks for an item and quantity with the Toad Bot's /bankrequest, the hub shall record a pending request under their Discord account and show it on the officers' request desk
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    When the Toad Bot asks for 4 "Flask of Relentless Assault" for the raider
    Then the request desk shows a pending request from "Hopscotch" for 4 "Flask of Relentless Assault" asked from Discord

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BDESK-002 When an officer approves or denies a pending request with a message, the hub shall record the answer, who gave it and when, queue a Toad Bot DM telling the member, and record it on the audit log
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    And the raider has asked for 4 "Flask of Relentless Assault" and 20 "Super Mana Potion"
    When the Wednesday officer approves the flasks with "Grab them from Gail after the raid"
    And the Wednesday officer denies the potions with "We are short this week"
    Then the flasks are approved and the potions denied, both by the Wednesday officer
    And the Toad Bot is asked to DM the raider each answer with its message
    And the audit log records "bank_desk.approve" and "bank_desk.deny" for Wednesday

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-BDESK-003 If anyone but an officer, or a member a super admin granted the bank's upkeep, lists or answers the bank's requests, then the hub shall refuse it and change nothing
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    And the raider has asked for 4 "Flask of Relentless Assault" and 20 "Super Mana Potion"
    Then the raider cannot see or answer the request desk
    And the Toad Bot's token cannot answer a request for an officer
    And a Sunday officer sees the same request desk under Sunday
    And both requests are still pending

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-BDESK-004 The hub shall keep every request a member makes with its answer, list a member their own requests, and list officers any member's requests
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    And the raider has asked for 4 "Flask of Relentless Assault" and 20 "Super Mana Potion"
    When the Wednesday officer approves the flasks with "Grab them from Gail after the raid"
    And another member asks for 1 "Drums of Battle" on the site
    Then the raider's own requests list the potions pending and the flasks approved, newest first
    And the officer's view of the raider's history lists the same two requests

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-BDESK-005 If a request has already been answered, then the hub shall refuse a second answer and send no second DM
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    And the raider has asked for 4 "Flask of Relentless Assault" and 20 "Super Mana Potion"
    When the Wednesday officer approves the flasks with "Grab them from Gail after the raid"
    Then denying the flasks is refused as already answered
    And the Toad Bot is asked for just one DM

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BDESK-006 When the Toad Bot has sent an answer's DM, or tells the hub it could not, the request desk shall show the DM as sent, or as failed with Discord's reason
    Given a Wednesday officer
    And a raider who goes by the nickname "Hopscotch"
    And the raider has asked for 4 "Flask of Relentless Assault" and 20 "Super Mana Potion"
    When the Wednesday officer approves the flasks with "Grab them from Gail after the raid"
    And the Wednesday officer denies the potions with "We are short this week"
    And the Toad Bot sends the flasks' DM and fails the potions' with "Discord refused: 403 Cannot send messages to this user"
    Then the request desk shows the flasks' DM sent and the potions' DM failed with "Discord refused: 403 Cannot send messages to this user"

  @ears_state_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-BDESK-007 While the launch hold keeps the Bank page's Forever preview, the officers' held Bank page shall still show the request desk, so officers can work requests before launch
    Given the officers' held Bank page
    Then it shows the request desk above the Forever preview
