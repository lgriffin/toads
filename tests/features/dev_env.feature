# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV ENV

  @ears_ubiquitous @maintainer @phase_2_0 @pending
  Scenario: REQ-DEV-ENV-001 A clean machine with Docker and uv shall run every service with seeded data by just up && just seed in under 10 minutes

  @ears_ubiquitous @maintainer @phase_1_0 @phase_2_0 @pending
  Scenario: REQ-DEV-ENV-002 Local just test shall run in the same container image CI uses, so local and CI results are identical
