# Highlight reels (clips) and member spotlights.
Feature: HUB SPOT

  @ears_ubiquitous @member @maintainer @phase_2_5
  Scenario: REQ-HUB-SPOT-001 The hub shall accept highlight reels only as https links to YouTube, Twitch clips or Streamable, and shall store only the provider and clip id
    Given the demo guild
    Then a YouTube, a Twitch and a Streamable link are accepted as provider and clip id
    And a link to any other host, or over http, is refused

  @ears_event_driven @raid_leader @phase_2_5
  Scenario: REQ-HUB-SPOT-002 When a raider submits a clip, the hub shall hold it until a global officer publishes it to the public story, publishes it to the guild, or rejects it
    Given the demo guild
    When the raider submits a clip
    Then nobody sees it yet
    When the global officer publishes it to the guild
    Then members see it and the public story does not

  @ears_unwanted_behavior @member @phase_2_5
  Scenario: REQ-HUB-SPOT-003 If a spotlight's member has not agreed to it, then the hub shall not publish it, and withdrawing agreement shall take it down at once
    Given the demo guild
    When the global officer writes a spotlight about the raider
    Then publishing it is refused with 409
    When the raider agrees to it
    And the global officer publishes it
    Then the public story shows it
    When the raider withdraws agreement
    Then the public story does not show it
