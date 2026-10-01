# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
# The bank's data and rules live in ToadsBank (lgriffin/ToadsBank); the hub is its website and Discord face
# (docs/bank.md). REQ-HUB-BANK-021 onwards describe that adapter; the TB-* ids are ToadsBank's own requirements.
Feature: HUB BANK

  @ears_ubiquitous @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-001 The Bank page shall show every item in the latest snapshot with icon, name, count and tab, and the snapshot's age and uploader at the top

  @ears_event_driven @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-002 When a member requests an item, the hub shall record quantity, character and reason and post the request to #bank-requests within 1 minute

  @ears_event_driven @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-003 When a request is approved or denied, the hub shall DM the member the decision and the officer's note within 5 minutes

  @ears_state_driven @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-004 While a request is open, the member shall be able to cancel it; after a decision they shall not

  @ears_ubiquitous @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-005 A member shall see their own receipts ledger on /me: every hand-out with item, date and the request it came from

  @ears_unwanted_behavior @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-006 If the latest snapshot is older than 7 days, then the Bank page shall say so and show the last upload time in the request form

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-010 The officer queue shall show, beside each open request, the requester's tier-weighted receipts for the last 90 days, request count and days since last hand-out

  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-011 When an officer approves or denies, the hub shall write the decision with officer, time and note to bank_decisions, and this shall never be deleted

  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-012 When a snapshot's log shows a withdrawal matching an approved request, the hub shall mark it handed out and link the transaction

  @ears_unwanted_behavior @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-013 If an approved request has no matching withdrawal after 14 days, then the hub shall expire it and list it under "approved, not handed out"

  @ears_unwanted_behavior @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-014 If a withdrawal has no request behind it, then the hub shall list it under "withdrawn without request" with actor and item

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-015 The Fairness view shall rank members by tier-weighted receipts over a chosen window and link each row to that member's ledger

  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-016 When an officer changes an item's tier, the hub shall record who and when and recompute weights without altering past decisions

  @ears_optional @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-017 Where the guild has enabled the public ledger flag, raiders shall see all members' receipts

  @ears_ubiquitous @raid_leader @phase_2_7 @pending
  Scenario: REQ-HUB-BANK-018 The History page's Bank tab shall show item flow over time and the full decision log, searchable by member and item

  @ears_ubiquitous @member @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-007 The Bank page shall list each of the raid day's bank sources separately with its own snapshot age and capturing character, and a request shall name the source that holds the item

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-019 The global aggregate bank view shall show every registered source's contents in one inventory with a source column, and the queue across all days

  # ToadsBank keys a source by guild, realm and region and lets its managers, officers and admins accept (TB-BM-10).
  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-020 When a global officer registers a bank source (bank guild, realm, capturing character, raid day), the hub shall accept snapshots for it only from a session that has claimed that character or from a global officer

  @ears_ubiquitous @member @phase_2_6
  Scenario: REQ-HUB-BANK-021 The Bank page shall show each bank source the member may see with its freshness and observation age, and an inventory of observed, pending outgoing, raid held, reserved and available counts with the capture-time range (TB-GM-02, TB-GM-03)
    Given the guild bank is set up with one captured bank
    When a member opens the bank
    Then they see "Toads main bank" marked fresh with its observation time
    And the inventory shows 40 "Super Mana Potion" observed and 40 available with a capture-time range

  @ears_event_driven @member @phase_2_6
  Scenario: REQ-HUB-BANK-022 When a member requests an item, the hub shall ask ToadsBank in that member's name to reserve it, and when stock is short shall offer a waitlisted request instead (TB-GM-05, TB-GM-06)
    Given the guild bank is set up with one captured bank
    When a member requests 500 "Super Mana Potion"
    Then the request is refused as insufficient stock with the waitlist offered
    When the member asks for the waitlist instead
    Then their request is waitlisted in their own name

  @ears_state_driven @member @phase_2_6
  Scenario: REQ-HUB-BANK-023 While a request is open, the member shall be able to cancel it, and an action carrying a stale revision shall be refused with the request's current state (TB-GM-07, TB-BM-16)
    Given the guild bank is set up with one captured bank
    And a member has requested 5 "Super Mana Potion"
    When the member cancels it with an old revision
    Then the hub refuses it as stale and shows the current revision
    When the member cancels it with the current revision
    Then the request is cancelled and the stock is free again

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-BANK-024 When an officer pastes a ToadsBank export, the hub shall report the parts received and missing, preview the complete snapshot and accept it on the officer's word (TB-BM-06, TB-BM-09)
    Given the guild bank is set up with one captured bank
    When a Wednesday officer pastes the first part of a new export
    Then the hub reports that part received and the rest missing
    When the officer pastes the remaining parts in reverse order
    Then the preview names "Toads main bank" and warns that tab 3 was not readable
    And accepting it updates tabs 1 and 2 and keeps tab 3 as it was

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-BANK-025 When ToadsBank assigns a request, the bank bot shall DM each manager with Approve, Reject and Record delivery buttons carrying the request's revision, and post to the fallback channel once a DM finally fails (TB-BM-11, TB-BM-12)
    Given the guild bank is set up with one captured bank
    And the bank bot's fallback channel is 302
    When ToadsBank reports a request assigned to managers 1234 and 5555
    Then the bank bot is asked to DM 1234 and 5555 with buttons for revision 2
    When every attempt to DM 1234 fails
    Then the bank bot is asked to post in channel 302 that a manager could not be reached

  @ears_unwanted_behavior @maintainer @phase_2_6
  Scenario: REQ-HUB-BANK-026 If a ToadsBank event arrives without the bank's service token or a second time, then the hub shall refuse it or acknowledge it without acting again (TB-DM-09)
    Given the guild bank is set up with one captured bank
    Then an event sent with the hub's own bot token is refused with 401
    When ToadsBank sends the same request update twice
    Then the requester is DMed once

  @ears_ubiquitous @maintainer @phase_2_6
  Scenario: REQ-HUB-BANK-027 The hub shall call ToadsBank with its service token and the member's Discord id, percent-encoded name and roles, and shall bind every idempotency key to the member and route
    Given ToadsBank is listening
    When a global officer called "Höps" asks for the bank's sources and makes a request
    Then ToadsBank hears the service token, their Discord id, "H%C3%B6ps" and the roles "member,officer,admin"
    And the idempotency key it hears is not the one the officer sent

  @ears_unwanted_behavior @member @phase_2_6
  Scenario: REQ-HUB-BANK-028 If the bank is not configured or ToadsBank does not answer, then the bank routes shall say so with 503 bank_not_configured or 502 bank_unavailable
    Given a hub without the bank configured
    Then a member asking for the bank's sources gets 503 "bank_not_configured"
    Given ToadsBank is down
    Then a member asking for the bank's sources gets 502 "bank_unavailable"

  @ears_ubiquitous @member @phase_2_6
  Scenario: REQ-HUB-BANK-029 Every bank bot message shall escape names from the bank and from Discord and shall never ping anyone (TB-DM-08)
    Given the guild bank is set up with one captured bank
    When ToadsBank reports a request from "@everyone" for "Super *Mana* Potion" approved
    Then the DM shows both names as written, with their markdown and mention syntax escaped
    And the bank bot sends it with mentions suppressed

  @ears_event_driven @member @phase_2_6
  Scenario: REQ-HUB-BANK-030 When a member uses a /bank command or button in Discord, the bot shall act through the hub as that member, with the roles Discord gives them and no more (TB-GM-09)
    Given the guild bank is set up with one captured bank
    Then the bot acting for a Wednesday officer may open an import for Wednesday
    And the bot acting for a plain member may not
    And the bot acting for someone outside the server is refused
