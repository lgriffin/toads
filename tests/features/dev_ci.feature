# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV CI

  @ears_event_driven @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-CI-001 When a PR is opened, CI shall run lint, types, unit, BDD, contract, security and dependency audits and block merge on any failure

  @ears_unwanted_behavior @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-CI-002 If a requirement ID in this document has no scenario, or a scenario has no ID or persona tag, then the reqs job shall fail

  @ears_ubiquitous @maintainer @phase_1_3 @phase_2_0 @pending
  Scenario: REQ-DEV-CI-003 Coverage shall not fall below 70 for wcl-core/wcl-store and 80 for services/api and services/worker
