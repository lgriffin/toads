# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB MEDIA

  @ears_event_driven @member @phase_2_5 @pending
  Scenario: REQ-HUB-MEDIA-001 When a raider uploads a screenshot from a phone, the hub shall accept it in at most three taps after choosing the image

  @ears_optional @member @phase_2_5 @pending
  Scenario: REQ-HUB-MEDIA-002 Where the member ticks "post to Discord", the bot shall post the image with its caption to #screenshots within 1 minute
