# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB DAY

  @ears_ubiquitous @member @phase_2_3 @pending
  Scenario: REQ-HUB-DAY-001 A member's /me shall show raids from every raid day they raid on, each marked with its day

  @ears_state_driven @member @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-002 While a member holds a raider or trial role for a raid day, they shall see that day's raids, signups, roster and bank sources and no officer views

  @ears_event_driven @member @phase_2_4 @pending
  Scenario: REQ-HUB-DAY-003 When a raid day's event is created in Discord, the Home card shall show it to that day's members first and other days' events below

  @ears_ubiquitous @raid_leader @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-010 A raid-day officer shall see officer views (insights, boss insights, raid diff, claims queue, bank requests, fairness) only for their own day's raids, members and bank sources

  @ears_unwanted_behavior @raid_leader @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-011 If a raid-day officer requests a sibling day's officer view or acts on its data, then the hub shall answer 403 and record the attempt in the audit log

  @ears_event_driven @raid_leader @phase_2_1 @pending
  Scenario: REQ-HUB-DAY-012 When a raid is imported, the hub shall assign it to the raid day whose raid group overlaps the roster by more than 60%, else leave it unassigned for the global tier

  @ears_event_driven @raid_leader @phase_2_4 @pending
  Scenario: REQ-HUB-DAY-013 When a raid-day officer claims an unassigned raid for their day, the hub shall record who did so and post its card to that day's channel

  @ears_ubiquitous @raid_leader @phase_2_4 @pending
  Scenario: REQ-HUB-DAY-014 Analysis cards, signup summaries and bank requests shall go to the raid day's configured channels; guild-wide cards to #raid-logs

  @ears_ubiquitous @raid_leader @phase_2_7 @pending
  Scenario: REQ-HUB-DAY-015 A global officer shall see every raid day's views, the aggregate bank and a cross-day comparison; a raid-day officer shall not see the comparison unless the global tier enables it

  @ears_ubiquitous @raid_leader @phase_2_6 @pending
  Scenario: REQ-HUB-DAY-016 A bank request shall be decidable by a global officer, or by a raid-day officer only for a request on their own day's sources; the raid-day Fairness view shall cover that day and the global one every day

  @ears_ubiquitous @raid_leader @phase_2_7 @pending
  Scenario: REQ-HUB-DAY-017 Every audit row shall carry the raid day it concerns; the History page shall filter by day and the global tier shall see the whole log

  @ears_ubiquitous @maintainer @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-020 Raid days, their Discord roles, channels and bank sources shall be configuration, not code; adding a day or a source shall need no deploy

  @ears_ubiquitous @maintainer @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-021 The RBAC matrix test shall be generated over (tier × raid day × endpoint) and shall include a denial case for every officer endpoint reached with a sibling day's scope

  @ears_unwanted_behavior @maintainer @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-022 If a Discord role id in the raid-day config matches no role in the server, then the API shall fail startup naming the day and role

  @ears_ubiquitous @maintainer @phase_2_2 @pending
  Scenario: REQ-HUB-DAY-023 Raid-day scope shall be resolved from the route path and the session, never from a request body or query parameter
