# Seeded from the Toads Hub build spec's persona tables. Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: DEV CI

  @ears_event_driven @maintainer @phase_2_0
  Scenario: REQ-DEV-CI-001 When a PR is opened, CI shall run lint, types, unit, BDD, contract, security and dependency audits and block merge on any failure
    Given the CI workflow
    Then it runs on every pull request and on pushes to main
    And every check that needs no network or services runs locally as scripts/dev.py check
    And each CI job runs exactly its scripts/dev.py tasks
    And the ci-success job needs every other job and is the only job that can be skipped
    And ci-success fails when any job it needs failed, was cancelled or was skipped

  @ears_unwanted_behavior @maintainer @phase_2_0
  Scenario: REQ-DEV-CI-002 If a requirement ID in this document has no scenario, or a scenario has no ID or persona tag, then the reqs job shall fail
    Given a feature file
    Then a scenario without a REQ id fails the reqs check
    And a scenario without exactly one EARS tag fails the reqs check
    And a scenario without a persona tag fails the reqs check
    And a duplicated REQ id fails the reqs check
    And CI runs the reqs check

  @ears_ubiquitous @maintainer @phase_1_3 @phase_2_0 @pending
  Scenario: REQ-DEV-CI-003 Coverage shall not fall below 70 for wcl-core/wcl-store and 80 for services/api and services/worker

  @ears_event_driven @maintainer @phase_2_0
  Scenario: REQ-DEV-CI-004 When apps/web changes on main, CI shall publish a static build of the web app with sample data to GitHub Pages, marked as a preview
    Given the Pages workflow
    Then it runs on pushes to main that change apps/web
    And it builds apps/web with PREVIEW=1 under the Pages base path
    And it deploys that build to GitHub Pages
    And the web layout shows a sample-data banner in the preview build

  @ears_optional @maintainer @member @raid_leader @phase_2_0
  Scenario: REQ-DEV-CI-005 Where the web app is built as the Pages preview, it shall open signed out on the public landing page and offer a pretend sign-in as a raider or an officer
    Given the preview's pretend sign-in
    Then the landing page sends a signed-out visitor to it
    And it offers the raider and the officer view
    And the preview asks a signed-out visitor to sign in for member pages and keeps raiders out of the officer console

  @ears_optional @maintainer @raid_leader @phase_2_5
  Scenario: REQ-DEV-CI-006 Where the web app is built as the Pages preview, it shall also offer a pretend sign-in as a super admin, and only that view shall manage bank grants and officer tokens
    Given the preview's pretend sign-in
    Then it offers the super admin view
    And only the super admin view manages bank grants and officer tokens in the preview bank

  @ears_event_driven @maintainer @phase_2_0
  Scenario: REQ-DEV-CI-007 When CI passes on a push to main and deployment is enabled, the deploy workflow shall roll that commit out to the production server over SSH, one deploy at a time
    Given the deploy workflow
    Then it runs after CI completes on main, or by hand
    And it deploys only a successful push build while DEPLOY_ENABLED is true
    And it sends only the commit sha over SSH with a pinned host key
    And the deploy script accepts only a commit on main and takes a lock

  @ears_event_driven @maintainer @phase_2_0
  Scenario: REQ-DEV-CI-008 When lgriffin/warcraftlogs_project publishes a newer release, the analyzer release workflow shall open a PR pinning wcl-core, wcl-store and wcl-app to that release and merge it once CI passes on it
    Given the analyzer release workflow
    Then it looks for a release nightly, or by hand, while ANALYZER_RELEASES_ENABLED is true
    And it pins all three analyzer packages to the latest plain release and never steps back
    And it merges only a green analyzer PR that changes nothing but the pin
