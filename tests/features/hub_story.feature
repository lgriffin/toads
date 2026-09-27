# The outward story: what people outside the guild see without logging in.
Feature: HUB STORY

  @ears_ubiquitous @member @raid_leader @phase_2_3
  Scenario: REQ-HUB-STORY-001 The public story shall show the guild's progression, what it is recruiting, and the posts, highlight reels and spotlights officers published as public, without a login
    Given the demo guild
    And a public post, a guild post, a public highlight and a published spotlight
    When a visitor opens the public story
    Then they see the progression and the recruitment needs
    And they see the public post, the public highlight and the spotlight
    And they see nothing that was published only to the guild

  @ears_unwanted_behavior @member @phase_2_3
  Scenario: REQ-HUB-STORY-002 If a post, highlight or spotlight has not been published as public, then the public story shall not show it
    Given the demo guild
    And a Discord post waiting for review, a submitted highlight and a spotlight awaiting consent
    When a visitor opens the public story
    Then the story has no posts, highlights or spotlights
