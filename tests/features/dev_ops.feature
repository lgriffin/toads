# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV OPS

  @ears_ubiquitous @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-OPS-001 Every service shall expose /healthz and Prometheus metrics, and log JSON with a request id propagated from API to worker to bot

  @ears_event_driven @maintainer @phase_2_7 @pending
  Scenario: REQ-DEV-OPS-002 When the nightly backup runs, the hub shall upload a pg_dump to object storage; a monthly CI job shall restore it into an empty database and run the contract tests

  @ears_ubiquitous @maintainer @phase_2_3
  Scenario: REQ-DEV-OPS-003 The worker's scheduler shall rebuild the hub's analyzer widgets and performance numbers at start and then on a fixed interval, and a failed run shall not stop later runs
    Given the scheduler with the default intervals
    When the hub is down for the first run
    Then the analyzer widgets and performance numbers are published again 30 minutes later
