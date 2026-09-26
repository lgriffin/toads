# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB EVENT

  @ears_event_driven @raid_leader @phase_2_4 @pending
  Scenario: REQ-HUB-EVENT-001 When a scheduled event's RSVP list changes, the Home card shall show sign-ups by role within 5 minutes
