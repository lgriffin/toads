# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV DOC

  @ears_ubiquitous @maintainer @phase_1_3 @phase_2_0 @pending
  Scenario: REQ-DEV-DOC-001 The requirements table, the API reference and the CLI reference shall be generated in CI from feature files, OpenAPI and argparse respectively, never hand-edited
