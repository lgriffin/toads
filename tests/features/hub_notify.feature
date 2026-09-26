# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB NOTIFY

  @ears_optional @member @phase_2_4 @pending
  Scenario: REQ-HUB-NOTIFY-001 Where a member has turned off DMs on /me, the bot shall send no DMs to that member
