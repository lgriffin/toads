# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB AUDIT

  @ears_ubiquitous @raid_leader @phase_2_2 @pending
  Scenario: REQ-HUB-AUDIT-001 Every officer action (sync, import, delete, approve, reassign, history edit) shall be recorded with actor and time and be visible on the History page
