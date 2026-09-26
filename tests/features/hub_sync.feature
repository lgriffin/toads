# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB SYNC

  @ears_event_driven @raid_leader @phase_2_1 @phase_2_4 @pending
  Scenario: REQ-HUB-SYNC-001 When a new guild report appears on Warcraft Logs, the hub shall analyse it and post a card to #raid-logs within 30 minutes without officer action

  @ears_event_driven @raid_leader @phase_2_1 @pending
  Scenario: REQ-HUB-SYNC-002 When an officer pastes a report URL or runs /log, the hub shall validate the code, queue the analysis and show the queue position

  @ears_state_driven @raid_leader @phase_2_1 @pending
  Scenario: REQ-HUB-SYNC-003 While an analysis is queued or running, the Raids & Logs table shall show its status and the current stage

  @ears_unwanted_behavior @raid_leader @phase_2_1 @pending
  Scenario: REQ-HUB-SYNC-004 If a report code does not belong to the guild, then the hub shall refuse automatic import and require an officer to confirm it as a reference report

  @ears_unwanted_behavior @raid_leader @phase_2_1 @pending
  Scenario: REQ-HUB-SYNC-005 If Warcraft Logs returns 429 or 5xx, then the worker shall back off exponentially and retry up to three times before marking the job failed with the reason visible on the status page
