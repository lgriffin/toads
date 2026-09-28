# Two-way Discord bots (docs/bots.md). Edit scenarios here, in the same PR as the code.
# @pending scenarios have no steps yet; add steps and drop @pending when the requirement is implemented.
Feature: HUB BOT

  @ears_ubiquitous @maintainer @phase_2_4
  Scenario: REQ-HUB-BOT-001 Each Discord bot shall be a named spec of bindings that registers with the hub the site actions it carries out and the Discord events it sends
    Given the relay bot's spec
    When the bot registers with the hub
    Then the hub lists the relay bot with its "say" action and "message" event

  @ears_event_driven @maintainer @phase_2_4
  Scenario: REQ-HUB-BOT-002 When the site sends a bot an action, the bot shall carry it out in Discord and report the Discord ids it made back to the site
    Given the relay bot is registered and watching channel 111
    When the site asks the relay bot to say "Raid at 8" in channel 111
    And the bot runs its pending actions
    Then "Raid at 8" is posted in channel 111 without pings
    And the site learns the message id the post became

  @ears_event_driven @maintainer @phase_2_4
  Scenario: REQ-HUB-BOT-003 When a member writes in a bot's channel, the bot shall pass the message to the site once, and the site shall hand it to every listener for that bot and event
    Given the relay bot is registered and watching channel 111
    And a site feature listens for the relay bot's messages
    When a member writes "hello hub" in channel 111 twice over
    Then the site feature hears "hello hub" once

  @ears_unwanted_behavior @maintainer @phase_2_4
  Scenario: REQ-HUB-BOT-004 If the site sends a bot an action it did not declare, or a bot sends an event it did not declare, then the hub shall refuse it
    Given the relay bot is registered and watching channel 111
    Then the site cannot ask the relay bot to "ban_member"
    And the hub refuses a "reaction" event from the relay bot

  @ears_optional @raid_leader @member @phase_2_4 @pending
  Scenario: REQ-HUB-BOT-005 Where bot permissions are configured, each binding shall ask the gate whether the Discord member may use it before acting on their behalf
