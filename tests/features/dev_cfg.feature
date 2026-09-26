# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV CFG

  @ears_unwanted_behavior @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-CFG-001 If a required environment variable is missing, then the service shall exit at startup naming the variable, before opening any port
