# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: CORE BANK

  @ears_event_driven @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-001 When the addon's SavedVariables file changes, the exporter shall write bank_items.csv and bank_log.csv with a schema_version header within 30 seconds

  @ears_unwanted_behavior @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-002 If a CSV row is malformed or the schema version is unknown, then the upload shall be rejected whole with the row number, and no partial snapshot stored

  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-003 Snapshots with an identical content hash shall be ignored; transactions shall be deduplicated across overlapping snapshots

  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-004 The exporter shall parse a captured SavedVariables fixture to the committed golden CSVs byte-for-byte

  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-005 Every request transition shall be covered by a scenario; an illegal transition shall be refused with 409

  @ears_event_driven @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-006 When a release is tagged, the addon zip shall be published with its own SHA256SUMS beside the installer and wcl-cli image

  @ears_unwanted_behavior @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-007 If a CSV's bank_guild, realm and captured_by do not match a registered source, then the upload shall be rejected whole naming the triple

  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-008 Transactions shall be deduplicated within a source only; two sources with identical rows shall both be kept
