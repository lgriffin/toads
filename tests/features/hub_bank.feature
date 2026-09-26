# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
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

  @ears_event_driven @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-BANK-020 When a global officer registers a bank source (bank guild, realm, capturing character, raid day), the hub shall accept snapshots for it only from a session that has claimed that character or from a global officer
