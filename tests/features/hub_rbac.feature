# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB RBAC

  @ears_ubiquitous @raid_leader @phase_2_2 @pending
  Scenario: REQ-HUB-RBAC-001 Officer permissions shall derive from Discord roles alone; no hub-side role assignment shall exist

  @ears_event_driven @raid_leader @phase_2_2 @phase_2_4 @pending
  Scenario: REQ-HUB-RBAC-002 When a Discord role is added or removed, the hub shall reflect the change within 15 minutes and on the member's next login, whichever is sooner
