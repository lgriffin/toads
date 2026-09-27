# Members' own Warcraft Logs API keys. Added for member settings; not yet in the build spec's tables.
Feature: HUB KEY

  @ears_optional @member @phase_2_2
  Scenario: REQ-HUB-KEY-001 Where a member has saved their own Warcraft Logs key, the worker shall use it instead of the guild key for requests made on that member's behalf
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    When they save their own Warcraft Logs key
    Then work done for them uses their key
    And work done for the guild still uses the guild key
    When they remove their key
    Then work done for them uses the guild key

  @ears_ubiquitous @member @phase_2_2
  Scenario: REQ-HUB-KEY-002 The hub shall store a member's Warcraft Logs key encrypted and shall never return or log it once saved
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    When they save their own Warcraft Logs key
    Then their settings show only the last four characters of the client id
    And the database holds neither the client id nor the secret in plain text
    And no log line carries the client id or the secret

  @ears_unwanted_behavior @member @phase_2_2
  Scenario: REQ-HUB-KEY-003 If Warcraft Logs refuses a member's key, then the worker shall use the guild key for that request and the member's settings shall show the key as rejected
    Given a Wednesday raider signed in with server nickname "Hopscotch"
    When they save their own Warcraft Logs key
    And Warcraft Logs refuses that key
    Then work done for them uses the guild key
    And their settings show the key as rejected
