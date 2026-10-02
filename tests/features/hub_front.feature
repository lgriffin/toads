# The public front door and the toolkit that explains what each tier can do. Edit scenarios here, in the same PR as
# the code. Design map: the "Toads Front Door Map" artifact in the Toads project (2026-10-02).
Feature: HUB FRONT

  @ears_ubiquitous @member @phase_2_5
  Scenario: REQ-HUB-FRONT-001 The public homepage shall explain how a Toads raid night works (prep, flasks and elixirs, consumes, speed, badges and how the guild measures itself) and shall show only guild-level numbers, never a player's name
    Given the public homepage
    Then it shows the six pillars of how we raid, each linking to its full write-up on How we raid
    And each pillar says what we expect, how we measure it and what a member sees
    And it shows a raid week and the three apps a member gets
    And its guild pulse reads only guild totals from the raid sheets
