# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB RBAC

  @ears_ubiquitous @raid_leader @phase_2_2
  Scenario: REQ-HUB-RBAC-001 Officer permissions shall derive from Discord roles alone; no hub-side role assignment shall exist
    Given a Wednesday officer signed in
    Then their session reports officer standing for raid day "wed" only
    And no route or table assigns hub roles

  @ears_event_driven @raid_leader @phase_2_2 @phase_2_4
  Scenario: REQ-HUB-RBAC-002 When a Discord role is added or removed, the hub shall reflect the change within 15 minutes and on the member's next login, whichever is sooner
    Given a Wednesday officer signed in
    When they gain the Sunday raider role in Discord
    And 15 minutes pass
    Then their session reports raider standing for raid day "sun"
    When their Wednesday officer role is removed in Discord
    And 15 minutes pass
    Then their next request is refused and the session is gone
