# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV REL

  @ears_ubiquitous @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-REL-001 No compose file shall reference a latest image tag; production shall run only signed images

  @ears_unwanted_behavior @maintainer @phase_2_1 @pending
  Scenario: REQ-DEV-REL-002 If a migration fails during deploy, then no new API or worker container shall start serving

  @ears_event_driven @maintainer @phase_2_7 @pending
  Scenario: REQ-DEV-REL-003 When just rollback <tag> is run, the previous images shall be serving and the schema downgraded within 5 minutes; CI shall exercise this on every release
