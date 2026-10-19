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

  @ears_event_driven @maintainer @phase_2_1
  Scenario: REQ-DEV-OPS-004 When the worker's sync runs, it shall analyse and store the guild's Warcraft Logs reports that are not stored yet, newest first and at most a batch per run when a batch is set, and a report that fails shall neither stop the others nor take a place in the batch
    Given the guild's reports on Warcraft Logs are "A, B, C, D", newest first, and "D" is stored
    And "A" fails to analyse
    When the sync runs with a batch of 2
    Then "B, C" are stored, "A" is listed as failed and 1 report is left for the next run

  @ears_event_driven @maintainer @phase_2_1
  Scenario: REQ-DEV-OPS-005 When the worker's sync runs, it shall keep importing the guild's new reports while the guild key's Warcraft Logs points left this hour, less a reserve, cover the dearest report so far, and shall stop once they do not
    Given the guild key may spend 1000 Warcraft Logs points an hour, 20 percent of them kept in reserve
    And 5 new guild reports that cost 300 points each
    When the sync runs with no batch set
    Then 2 reports are stored and the run stops on the rate-limit budget

  @ears_event_driven @maintainer @phase_2_1
  Scenario: REQ-DEV-OPS-006 When a super admin runs the worker's backfill, it shall import every guild report on Warcraft Logs not stored yet, oldest first, waiting for the rate limit to reset whenever the hour's points are spent, and shall finish once only reports that fail to analyse are left
    Given the guild key may spend 1000 Warcraft Logs points an hour, 20 percent of them kept in reserve
    And 5 new guild reports that cost 300 points each
    And the third oldest of them fails to analyse
    When the backfill runs
    Then the other 4 reports are stored, oldest first, after waiting for the rate limit to reset 2 times
