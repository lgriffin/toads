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

  # Super admins and the break-glass admin (docs/admin.md): two or three people named in configuration, above the
  # global officers. They hand bank permissions out directly or through officer tokens.
  @ears_ubiquitous @maintainer @phase_2_6
  Scenario: REQ-HUB-RBAC-003 Super admins shall be named by Discord user id in the hub's configuration alone, shall hold every power a global officer holds, and shall be the only members who grant or revoke bank permissions and mint officer tokens
    Given the guild bank is set up with one captured bank
    Then the super admin's session reports them as a super admin and a global officer
    And the super admin may grant, list and revoke bank grants
    And a global officer may list bank grants but not grant or revoke them
    And no route or table makes anyone a super admin

  @ears_ubiquitous @maintainer @phase_2_6
  Scenario: REQ-HUB-RBAC-004 The break-glass admin named in the hub's configuration shall always be a super admin, shall be shown as such in their session and on the bank page, and every change they make shall be on the audit log marked break_glass
    Given the guild bank is set up with one captured bank
    Then the break-glass admin's session and bank standing say break glass
    And the global tier's bank standing names the break-glass admin
    When the break-glass admin mints an officer token
    Then the audit log marks the mint as a break-glass change
