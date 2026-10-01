# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
# The CSV exporter these describe is superseded by ToadsBank (lgriffin/ToadsBank): its addon exports a snapshot as
# TOADSBANK/1 text parts that members paste into Discord or the site (docs/bank.md). Each scenario names the ToadsBank
# requirement that replaces it; they stay here, pending, as the record of the original plan.
Feature: CORE BANK

  # Superseded by ToadsBank TB-BM-05 (the addon presents the snapshot as pasteable parts of at most 1,800 characters).
  @ears_event_driven @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-001 When the addon's SavedVariables file changes, the exporter shall write bank_items.csv and bank_log.csv with a schema_version header within 30 seconds

  # Superseded by ToadsBank TB-BM-06 and TB-DM-07 (reassembly, CRC and schema checks; an import is accepted whole or not at all).
  @ears_unwanted_behavior @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-002 If a CSV row is malformed or the schema version is unknown, then the upload shall be rejected whole with the row number, and no partial snapshot stored

  # Superseded by ToadsBank TB-BM-07 (a repeated snapshot id returns the earlier receipt; different content is refused).
  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-003 Snapshots with an identical content hash shall be ignored; transactions shall be deduplicated across overlapping snapshots

  # Superseded by ToadsBank TB-DM-03 (the Lua and TypeScript codecs validate against the same checked-in fixtures).
  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-004 The exporter shall parse a captured SavedVariables fixture to the committed golden CSVs byte-for-byte

  # Superseded by ToadsBank TB-DM-06 and TB-BM-16 (revisions and idempotency keys; stale or invalid transitions are 409).
  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-005 Every request transition shall be covered by a scenario; an illegal transition shall be refused with 409

  # Superseded by ToadsBank TB-DM-11 (one release tag publishes the images and the addon archive).
  @ears_event_driven @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-006 When a release is tagged, the addon zip shall be published with its own SHA256SUMS beside the installer and wcl-cli image

  # Superseded by ToadsBank TB-BM-10 (exports resolve to a registered source by guild, realm and region, else unknown_source).
  @ears_unwanted_behavior @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-007 If a CSV's bank_guild, realm and captured_by do not match a registered source, then the upload shall be rejected whole naming the triple

  # Superseded by ToadsBank TB-BM-10 and TB-BM-15 (one source per physical bank; movement is matched within a source).
  @ears_ubiquitous @maintainer @phase_2_6 @pending
  Scenario: REQ-CORE-BANK-008 Transactions shall be deduplicated within a source only; two sources with identical rows shall both be kept
