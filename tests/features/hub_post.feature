# Officer posts that flow both ways between Discord and the hub, curated by officers.
Feature: HUB POST

  @ears_event_driven @raid_leader @phase_2_4
  Scenario: REQ-HUB-POST-001 When a message is posted in a mirrored Discord channel, the hub shall hold it for an officer and show it nowhere until an officer publishes it
    Given the demo guild
    When the bot mirrors an announcement
    Then members do not see it
    When the global officer publishes it to the guild
    Then members see it marked as from Discord

  @ears_event_driven @raid_leader @phase_2_4
  Scenario: REQ-HUB-POST-002 When an officer publishes a hub post and ticks "also post to Discord", the bot shall post it to the configured channel, and edits on the hub shall edit that Discord message
    Given the demo guild
    When the global officer writes a post and ticks also post to Discord
    Then the bot is asked to post it to the guild posts channel
    When the bot reports the Discord message it sent
    And the global officer edits the post
    Then the bot is asked to edit that Discord message

  @ears_unwanted_behavior @raid_leader @phase_2_4
  Scenario: REQ-HUB-POST-003 If a post published to the public story is edited in Discord, then the hub shall take it off the public story until an officer reviews it again
    Given the demo guild
    And a mirrored announcement published as public
    When its author edits it in Discord
    Then it is waiting for review again and flagged as edited
    And the public story does not show it

  @ears_event_driven @member @phase_2_4
  Scenario: REQ-HUB-POST-004 When a mirrored message is deleted in Discord, the hub shall hide its post
    Given the demo guild
    And a mirrored announcement published as public
    When its author deletes it in Discord
    Then nobody sees it on the hub

  @ears_ubiquitous @maintainer @phase_2_4
  Scenario: REQ-HUB-POST-005 Nothing the bot posts or the hub mirrors shall ping @everyone, @here or a role
    Given the demo guild
    When the bot mirrors "@everyone raid in 5 @here"
    Then the stored post cannot ping anyone
    And the bot sends officer posts with every mention type switched off

  @ears_unwanted_behavior @raid_leader @phase_2_2 @phase_2_4
  Scenario: REQ-HUB-POST-006 If a raid-day officer tries to publish to the public story or act on a sibling raid day's post, then the hub shall refuse
    Given the demo guild
    And a Wednesday Discord message is waiting for review
    Then the Wednesday officer cannot publish it as public
    And the Sunday officer cannot see or curate it

  @ears_unwanted_behavior @maintainer @phase_2_4
  Scenario: REQ-HUB-POST-007 If the bot offers a message from a channel that is not in the hub's mirror list, then the hub shall refuse it
    Given the demo guild
    Then a message from an unlisted channel is refused
