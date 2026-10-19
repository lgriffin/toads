# The public front door and the toolkit that explains what each tier can do. Edit scenarios here, in the same PR as
# the code. Design map: the "Toads Front Door Map" artifact in the Toads project (2026-10-02).
Feature: HUB FRONT

  @ears_ubiquitous @member @phase_2_5
  Scenario: REQ-HUB-FRONT-001 The public homepage shall explain how a Toads raid night works (prep, flasks and consumes, speed and how the guild measures itself) and shall show only guild-level numbers, never a player's name
    Given the public homepage
    Then it shows the raid-night pillars, each linking to its full write-up on How we raid
    And How we raid says for each of its six pillars what we expect, how we measure it and what a member sees, with the Loot Council in place of badges
    And it shows the three apps a member gets and that they open through the hub at the Forever launch
    And its guild pulse reads only guild totals from the raid sheets

  @ears_ubiquitous @member @raid_leader @phase_2_5
  Scenario: REQ-HUB-FRONT-002 The public Hub features page shall show what everyone, raiders and officers can do in the raid analyzer, the guild bank and Discord with the officers' Google Drive, mark the steps up to the viewer's tier, and name only permissions the hub's RBAC table gives that tier
    Given the Hub features page
    Then it lists the raid analyzer, the guild bank and Discord and Drive, each with a step for every tier
    And it marks the steps up to the viewer's tier, read from their session, and shows super admins the officers' steps
    And a unit test fails if a step names a permission the RBAC table lacks or gives another tier
    And it is in the public nav, the top bar's tier chip opens it and the old toolkit address redirects to it

  @ears_event_driven @member @maintainer @phase_2_5
  Scenario: REQ-HUB-FRONT-003 When a member is new to the hub, it shall offer a welcome checklist, and it shall give super admins one console for bank grants, officer tokens and the hub's integrations
    Given the welcome checklist
    Then it walks a new member through claiming characters, their name, how we raid, the bank, the apps and the hub's features
    And the admin console shows integrations, scheduled jobs and bank grants to super admins only

  @ears_state_driven @member @raid_leader @phase_2_5
  Scenario: REQ-HUB-FRONT-004 While the launch hold is on, the hub shall show a signed-in raider one coming-soon page for the guild bank, logs analysis and raid assistance, show officers every page as it is being built except the bank, which shows a Forever launch notice, and show super admins exactly the officers' view plus the Admin console
    Given the launch hold
    Then a raider's members nav is the hub link alone and every member page shows the coming-soon page
    And an officer opens every page but the bank, which shows the Forever launch notice
    And super admins see exactly what officers see, plus the Admin console
    And visitors and the public pages are never held
    And the real site waits for the session before a held page renders, so it never starts the page's own API calls

  @ears_state_driven @member @raid_leader @phase_2_5
  Scenario: REQ-HUB-FRONT-005 While the launch hold is on, the Bank tab shall show officers its intent, the features coming to it and a labelled mockup of stock, Discord requests, a ledger and a fairness view, and every signed-in member shall meet their own toad
    Given the tab previews
    Then the Bank tab states its intent and lists what is coming
    And the Bank tab shows the bankers' features to officers and a mockup labelled as sample data
    And every signed-in member has a rank toad, raiders the member toad
    And raiders meet their toad on the coming-soon page, officers on the held bank tab, and everyone on the hub home

  @ears_ubiquitous @member @maintainer @phase_2_5
  Scenario: REQ-HUB-FRONT-006 The public Story page's tagline and story shall come from the repository, so a merge and the deploy that follows change them without editing the server
    Given the Story page's words
    Then the API serves the tagline and story from the repository, not from config/community.yaml
    And the static preview shows the same words

  @ears_state_driven @member @phase_2_5
  Scenario: REQ-HUB-FRONT-007 While the launch hold is on, the story page shall show our story alone: the hero, the Discord link and the story, without recruiting, progression, highlights or news
    Given the public launch hold
    Then the story page shows only the story while the hold is on and the full story page after it
    And the homepage and every public tab stay open to visitors

  @ears_ubiquitous @member @phase_2_5
  Scenario: REQ-HUB-FRONT-008 Every page shall show The Regular toad as its browser tab icon, as an SVG with an ICO fallback and a home-screen icon
    Given the page shell
    Then it links the toad as an SVG icon, an ICO icon and an Apple touch icon under the site's asset path
    And the SVG icon is The Regular toad from the logo set and the icon files are in the web app's static folder
